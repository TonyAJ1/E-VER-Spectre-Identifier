"""T-16a-2: etiquetado, deduplicación y split del conjunto Chemotion IR.

    python -m herramientas.dataset.etiquetar

Necesita RDKit (herramientas/dataset/requisitos.txt), el conjunto descargado y
el índice de T-16a-1 (datos/dataset/indice.csv).

Qué hace, en orden:

1. Elige un archivo por análisis, el original antes que el derivado, igual que
   la medición de T-16a-1.
2. Prepara cada uno por la ruta de producción (herramientas/entrenamiento/
   preparar.py, T-16b), así que el vector es el mismo que vería la aplicación.
3. Quita los espectros repetidos. Si el mismo vector aparece con dos InChIKey
   distintos se quitan todos los que lo comparten, porque al menos una de las
   estructuras está mal y no se sabe cuál.
4. Etiqueta los siete grupos a partir del SMILES con el criterio D-24 v2 del
   traspaso (sección 4.1). Cada celda vale 1, 0 o x. La x es una celda
   enmascarada (sección 4.2): el grupo no se puede decidir para ese compuesto,
   así que el entrenamiento y la evaluación la ignoran, pero los otros seis
   grupos del mismo compuesto sí se usan.
5. Parte 70, 15 y 15 por compuesto (InChIKey), con semilla fija, cuidando que
   los grupos raros caigan en los tres conjuntos (sección 4.3).

Escribe datos/dataset/conjunto.csv, datos/dataset/split-prueba.txt y deja los
vectores en datos/dataset/vectores.npz, que no se sube al repositorio porque
deriva de los espectros (licencia CC BY-SA, ver ORIGEN.md).

PROVISIONAL: D-24 v2 y las secciones 4.2 a 4.4 del traspaso no están firmadas
por el equipo. Los casos que el traspaso deja sin decidir se enmascaran, que es
la opción que no inventa una etiqueta. Si el equipo decide otra cosa, se
cambian las reglas de abajo y se vuelve a correr: el split depende solo de los
InChIKey y de la semilla, no de las etiquetas de los grupos comunes.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from rdkit import Chem, RDLogger

from backend.utilerias.catalogo import obtener as obtener_catalogo
from herramientas.dataset.descargar_chemotion import DESTINO, RAIZ
from herramientas.dataset.embudo_chemotion import (
    INDICE,
    PASA,
    adjuntos,
    recibir_archivo,
    tipo_adjunto,
)
from herramientas.entrenamiento.preparar import preparar

CARPETA = RAIZ / "datos" / "dataset"
CONJUNTO = CARPETA / "conjunto.csv"
SPLIT_PRUEBA = CARPETA / "split-prueba.txt"
VECTORES = CARPETA / "vectores.npz"

SEMILLA = 20261124
PROPORCIONES = {"entrenamiento": 0.70, "validacion": 0.15, "prueba": 0.15}
ENMASCARADA = "x"

#: Los elementos que entran en química orgánica de síntesis. Un compuesto con
#: cualquier otro (metales sobre todo) se excluye entero: la coordinación corre
#: las bandas de los ligandos y el espectro ya no corresponde a la estructura
#: libre (D-24 v2, último caso de la tabla).
ELEMENTOS_ORGANICOS = {"H", "B", "C", "N", "O", "F", "Si", "P", "S", "Cl", "Se", "Br", "I"}


def _patron(texto: str) -> Chem.Mol:
    patron = Chem.MolFromSmarts(texto)
    if patron is None:  # pragma: no cover - error de quien escribe el patrón
        raise ValueError(texto)
    return patron


#: Lo que hace que cada grupo valga 1. Los nombres siguen al catálogo.
POSITIVO = {
    # Alcohol, fenol y ácido: un O con H unido a carbono (propuesta v2.6).
    "GF-01": [_patron("[OX2H][#6]")],
    # N con al menos un H: aminas primarias y secundarias, amidas, NH
    # aromático y sales de amonio. Una amina terciaria no cuenta.
    "GF-02": [_patron("[#7;!H0]")],
    # Carbono sp3 con al menos un H.
    "GF-03": [_patron("[CX4;!H0]")],
    # Nitrilo.
    "GF-04": [_patron("[NX1]#[CX2][#6]")],
    # Carbonilo, amida y ácido incluidos (propuesta v2.6, caso abierto 1:
    # se etiqueta la química tal cual es).
    "GF-05": [_patron("[CX3]=[OX1]")],
    # Alqueno no aromático con su =C-H, que es lo que el catálogo usa para
    # distinguirlo (D-24 v2, caso de la amida).
    "GF-06": [_patron("[C;!a;!H0]=[C;!a]")],
    # Anillo aromático de carbono, como el benceno, con al menos un C-H
    # aromático (es lo que pide R-2 y lo que describe el catálogo).
    "GF-07": [_patron("[cH]1ccccc1")],
}

#: Lo que vuelve indecidible un grupo cuando el compuesto no lo tiene. Si el
#: grupo es positivo, la celda se queda en 1: el positivo no es dudoso.
DUDOSO = {
    # Oxima: O-H sobre N, banda ancha que el rasgo no separa. Agua o un
    # O-H sobre otro átomo (ácidos de P, S, B): mismo problema.
    "GF-01": [
        ("oxima u O-H sobre otro átomo", _patron("[OX2H][!#6]")),
        ("agua de cristalización", _patron("[OH2]")),
    ],
    # Alquino terminal: el C-H de 3300 es agudo y R-1 lo confunde con N-H.
    # Marginal sin decidir en el traspaso: se enmascara.
    "GF-02": [("alquino terminal", _patron("[CX2H]#[CX2]"))],
    # Alquino interno, isonitrilo, cianato y tiocianato caen en 2190-2260.
    "GF-04": [
        ("alquino interno", _patron("[CX2H0]#[CX2H0]")),
        ("isonitrilo", _patron("[NX2+]#[CX1-]")),
        ("cianato o tiocianato", _patron("[NX1]#[CX2][O,S,N]")),
    ],
    # Imina: C=N con C-H sp2 rozando 3020-3100. Marginal sin decidir: se
    # enmascara. Un alqueno sin H (tetrasustituido) no tiene el rasgo.
    "GF-06": [
        ("imina", _patron("[C;!a]=[N;!a]")),
        ("alqueno sin =C-H", _patron("[C;!a;H0]=[C;!a;H0]")),
    ],
    # Heteroaromático sin anillo de benceno, o benceno sin C-H aromático.
    "GF-07": [
        ("heteroaromático", _patron("[a;!c]")),
        ("benceno sin C-H", _patron("c1ccccc1")),
    ],
}


def etiquetas_de(smiles: str) -> tuple[dict[str, str] | None, str]:
    """Las siete celdas de un compuesto, o None y el motivo si se excluye."""
    molecula = Chem.MolFromSmiles(smiles)
    if molecula is None:
        return None, "SMILES no parseable"
    elementos = {atomo.GetSymbol() for atomo in molecula.GetAtoms()}
    ajenos = elementos - ELEMENTOS_ORGANICOS
    if ajenos:
        return None, "contiene " + ",".join(sorted(ajenos))
    celdas: dict[str, str] = {}
    motivos: list[str] = []
    for grupo, patrones in POSITIVO.items():
        if any(molecula.HasSubstructMatch(p) for p in patrones):
            celdas[grupo] = "1"
            continue
        dudas = [nombre for nombre, p in DUDOSO.get(grupo, []) if molecula.HasSubstructMatch(p)]
        if dudas:
            celdas[grupo] = ENMASCARADA
            motivos.append(f"{grupo}: {dudas[0]}")
        else:
            celdas[grupo] = "0"
    return celdas, "; ".join(motivos)


# --------------------------------------------------------------------------- #


def representantes() -> list[dict]:
    """Un archivo por análisis, el original antes que el derivado."""
    with INDICE.open(encoding="utf-8", newline="") as flujo:
        indice = {f["archivo"]: f for f in csv.DictReader(flujo)}
    orden = {".dx": 0, ".jdx": 1, ".peak.jdx": 2, ".edit.jdx": 3}
    por_analisis: dict[int, list[dict]] = defaultdict(list)
    for adjunto in adjuntos():
        fila = indice.get(adjunto["archivo"])
        if fila is None or fila["veredicto"] != PASA:
            continue
        adjunto["inchikey"] = fila["inchikey"]
        adjunto["tipo"] = tipo_adjunto(adjunto["nombre_original"])
        por_analisis[adjunto["analysis_id"]].append(adjunto)
    return [
        min(grupo, key=lambda f: (orden.get(f["tipo"], 9), f["archivo"]))
        for grupo in por_analisis.values()
    ]


def vectores(filas: list[dict]) -> np.ndarray:
    """La ventana del modelo de cada archivo, por la ruta de producción."""
    if VECTORES.exists():
        guardado = np.load(VECTORES, allow_pickle=False)
        if list(guardado["archivos"]) == [f["archivo"] for f in filas]:
            return guardado["vectores"]
    salida = []
    for n, fila in enumerate(filas, start=1):
        ruta = DESTINO / f"{fila['archivo']}.jdx"
        preparado = preparar(ruta.name, recibir_archivo(ruta).contenido or "")
        if preparado.vector is None:
            raise SystemExit(f"{ruta.name} pasó en T-16a-1 y ahora no: {preparado.codigo}")
        salida.append(preparado.vector)
        if n % 250 == 0:
            print(f"  ... {n} de {len(filas)}", file=sys.stderr, flush=True)
    matriz = np.asarray(salida, dtype=np.float32)
    np.savez_compressed(
        VECTORES, archivos=np.asarray([f["archivo"] for f in filas]), vectores=matriz
    )
    return matriz


def sin_repetidos(filas: list[dict], matriz: np.ndarray) -> tuple[list[int], Counter]:
    """Los índices que se quedan y por qué se fue cada uno de los demás."""
    por_huella: dict[str, list[int]] = defaultdict(list)
    for i, vector in enumerate(matriz):
        por_huella[hashlib.sha256(vector.tobytes()).hexdigest()].append(i)
    quedan, fuera = [], Counter()
    for indices in por_huella.values():
        claves = {filas[i]["inchikey"] for i in indices}
        if len(claves) > 1:
            fuera["mismo espectro con InChIKey distinto"] += len(indices)
            continue
        quedan.append(min(indices, key=lambda i: filas[i]["archivo"]))
        fuera["espectro repetido del mismo compuesto"] += len(indices) - 1
    return sorted(quedan), fuera


def partir(claves: list[str], celdas: dict[str, dict[str, str]], grupos: list[str]) -> dict[str, str]:
    """Reparte los compuestos en los tres conjuntos.

    Es una estratificación sencilla: los compuestos con los grupos más raros
    se reparten primero, cada uno al conjunto que más positivos de ese grupo
    le falta. Los demás se reparten al azar con la misma semilla.
    """
    azar = random.Random(SEMILLA)
    claves = sorted(claves)
    azar.shuffle(claves)
    positivos = Counter(g for k in claves for g in grupos if celdas[k][g] == "1")
    raros = sorted(grupos, key=lambda g: positivos[g])

    meta = {s: p * len(claves) for s, p in PROPORCIONES.items()}
    meta_grupo = {(s, g): p * positivos[g] for s, p in PROPORCIONES.items() for g in grupos}
    cuenta = Counter()
    cuenta_grupo = Counter()
    asignado: dict[str, str] = {}

    def poner(clave: str, conjunto: str) -> None:
        asignado[clave] = conjunto
        cuenta[conjunto] += 1
        for g in grupos:
            if celdas[clave][g] == "1":
                cuenta_grupo[conjunto, g] += 1

    for grupo in raros[:3]:
        for clave in claves:
            if clave in asignado or celdas[clave][grupo] != "1":
                continue
            conjunto = max(
                PROPORCIONES,
                key=lambda s: (meta_grupo[s, grupo] - cuenta_grupo[s, grupo], meta[s] - cuenta[s]),
            )
            poner(clave, conjunto)
    for clave in claves:
        if clave not in asignado:
            poner(clave, max(PROPORCIONES, key=lambda s: meta[s] - cuenta[s]))
    return asignado


def main() -> None:
    RDLogger.DisableLog("rdApp.*")
    logging.disable(logging.CRITICAL)
    grupos = [g.id for g in obtener_catalogo().grupos]

    filas = representantes()
    print(f"análisis con un archivo que pasa: {len(filas)}")
    matriz = vectores(filas)
    quedan, fuera = sin_repetidos(filas, matriz)
    print(f"espectros distintos: {len(quedan)}")
    for motivo, n in fuera.items():
        print(f"  fuera, {motivo}: {n}")

    salida, excluidos = [], Counter()
    for i in quedan:
        fila = filas[i]
        if not fila["inchikey"]:
            excluidos["sin InChIKey"] += 1
            continue
        celdas, motivo = etiquetas_de(fila["cano_smiles"])
        if celdas is None:
            excluidos[motivo.split(" ")[0] if motivo.startswith("contiene") else motivo] += 1
            continue
        salida.append({"indice": i, **fila, "celdas": celdas, "motivo": motivo})
    print(f"etiquetados: {len(salida)}")
    for motivo, n in excluidos.items():
        print(f"  excluidos, {motivo}: {n}")

    # Un compuesto con varios espectros: todas sus celdas deben coincidir,
    # porque salen del mismo SMILES. Se parte por InChIKey.
    por_clave = {f["inchikey"]: f["celdas"] for f in salida}
    split = partir(list(por_clave), por_clave, grupos)

    columnas = ["archivo", "analysis_id", "sample_id", "inchikey", *grupos, "enmascarado_por", "split"]
    with CONJUNTO.open("w", encoding="utf-8", newline="") as flujo:
        escritor = csv.writer(flujo)
        escritor.writerow(columnas)
        for f in sorted(salida, key=lambda f: f["archivo"]):
            escritor.writerow(
                [f["archivo"], f["analysis_id"], f["sample_id"], f["inchikey"],
                 *(f["celdas"][g] for g in grupos), f["motivo"], split[f["inchikey"]]]
            )

    prueba = sorted(k for k, s in split.items() if s == "prueba")
    texto = "\n".join(prueba) + "\n"
    SPLIT_PRUEBA.write_text(texto, encoding="utf-8")
    print(f"\nsplit-prueba.txt: {len(prueba)} compuestos, sha256 {hashlib.sha256(texto.encode()).hexdigest()}")

    print("\nsupport por grupo (positivos / celdas evaluables), por conjunto:")
    print("grupo   " + "  ".join(f"{s:>22}" for s in PROPORCIONES))
    for g in grupos:
        partes = []
        for s in PROPORCIONES:
            del_conjunto = [f for f in salida if split[f["inchikey"]] == s]
            evaluables = [f for f in del_conjunto if f["celdas"][g] != ENMASCARADA]
            pos = sum(f["celdas"][g] == "1" for f in evaluables)
            partes.append(f"{pos:>5} / {len(evaluables):<5} ({pos / max(len(evaluables), 1):.2f})")
        print(f"{g}   " + "  ".join(f"{p:>22}" for p in partes))
    print("espectros por conjunto:", dict(Counter(split[f["inchikey"]] for f in salida)))
    print("compuestos por conjunto:", dict(Counter(split.values())))

    print("\nceldas enmascaradas por motivo:")
    for motivo, n in Counter(
        m for f in salida for m in f["motivo"].split("; ") if m
    ).most_common():
        print(f"  {motivo}: {n}")

    print("\nco-ocurrencia (compuestos con los dos grupos en 1):")
    print("       " + " ".join(f"{g[-2:]:>5}" for g in grupos))
    for a in grupos:
        print(f"{a}  " + " ".join(
            f"{sum(c[a] == '1' and c[b] == '1' for c in por_clave.values()):>5}" for b in grupos
        ))


if __name__ == "__main__":
    main()
