"""T-16d: la evaluación de RNF-08 sobre el conjunto de prueba.

    python -m herramientas.entrenamiento.evaluar

Es la única corrida que abre el conjunto de prueba, y se corre una sola vez:
si docs/evidencia/rnf-08.md ya existe, se niega a correr. Si se ajustara algo
mirando estos números, el resultado de RNF-08 dejaría de significar nada.

Escribe las tablas que pide D-13, más dos de contexto:

1. La vía ML sola, con corte en 0.5.
2. El motor completo, con la fusión y el umbral de UT-03.
3. La vía de reglas sola, con el mismo umbral (contexto).
4. Un predictor que siempre dice que sí (contexto, sección 4.4 del traspaso):
   si un grupo es muy común, ese predictor ya saca un F1 alto sin aprender.

Las celdas enmascaradas no cuentan. Un grupo con menos de SUPPORT_MINIMO
positivos en prueba queda como informativo: su F1 no decide la puerta.
"""

from __future__ import annotations

import csv
import hashlib
import logging
import time
from datetime import date

from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.dataset.descargar_chemotion import DESTINO, RAIZ
from herramientas.dataset.embudo_chemotion import recibir_archivo
from herramientas.dataset.etiquetar import CONJUNTO, ENMASCARADA, SPLIT_PRUEBA
from herramientas.entrenamiento.preparar import espectro_redondeado
from motor_identificacion.inferencia import identificar, ventana_del_modelo
from motor_identificacion.inferencia.red import cargar_red

EVIDENCIA = RAIZ / "docs" / "evidencia" / "rnf-08.md"

#: La puerta de D-13: F1 de al menos 0.80 en estos tres grupos.
PUERTA = ("GF-01", "GF-04", "GF-05")
F1_PUERTA = 0.80
#: PROVISIONAL (sección 4.4 del traspaso, sin firmar): con menos positivos que
#: esto en prueba, un solo acierto mueve el F1 demasiado para decidir.
SUPPORT_MINIMO = 20


def metricas(reales: list[str], predichos: list[bool]) -> dict:
    vp = fp = fn = vn = 0
    for real, dice in zip(reales, predichos):
        if real == ENMASCARADA:
            continue
        positivo = real == "1"
        vp += positivo and dice
        fp += (not positivo) and dice
        fn += positivo and not dice
        vn += (not positivo) and not dice
    precision = vp / (vp + fp) if vp + fp else 0.0
    recall = vp / (vp + fn) if vp + fn else 0.0
    f1 = 2 * vp / (2 * vp + fp + fn) if vp + fp + fn else 0.0
    return {"vp": vp, "fp": fp, "fn": fn, "vn": vn, "precision": precision,
            "recall": recall, "f1": f1, "support": vp + fn, "n": vp + fp + fn + vn}


def tabla(titulo: str, resultados: dict[str, dict], grupos: list[str], nombres: dict[str, str]) -> list[str]:
    lineas = [f"### {titulo}", "",
              "| Grupo | Precisión | Recall | F1 | Support | Celdas | VP | FP | FN | VN |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for g in grupos:
        m = resultados[g]
        lineas.append(
            f"| {g} {nombres[g]} | {m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} "
            f"| {m['support']} | {m['n']} | {m['vp']} | {m['fp']} | {m['fn']} | {m['vn']} |"
        )
    macro = sum(resultados[g]["f1"] for g in grupos) / len(grupos)
    lineas += ["", f"Macro F1: **{macro:.3f}**", ""]
    return lineas


def main() -> None:
    if EVIDENCIA.exists():
        raise SystemExit(
            "docs/evidencia/rnf-08.md ya existe: el conjunto de prueba se usa una sola vez"
        )
    logging.disable(logging.CRITICAL)
    configuracion = obtener_configuracion()
    catalogo = obtener_catalogo()
    grupos = [g.id for g in catalogo.grupos]
    nombres = {g.id: g.nombre for g in catalogo.grupos}
    red = cargar_red(grupos_esperados=tuple(grupos))
    umbral = configuracion.motor.umbral_confianza

    with CONJUNTO.open(encoding="utf-8", newline="") as flujo:
        filas = [f for f in csv.DictReader(flujo) if f["split"] == "prueba"]

    reales = {g: [] for g in grupos}
    ml, motor, reglas = ({g: [] for g in grupos} for _ in range(3))
    tiempos = []
    for fila in filas:
        ruta = DESTINO / f"{fila['archivo']}.jdx"
        espectro, codigo = espectro_redondeado(ruta.name, recibir_archivo(ruta).contenido or "")
        if espectro is None:
            raise SystemExit(f"{ruta.name} no pasa: {codigo}")
        inicio = time.perf_counter()
        completo = identificar(espectro, red, catalogo, configuracion)
        tiempos.append(time.perf_counter() - inicio)
        solo_reglas = identificar(espectro, None, catalogo, configuracion)
        probabilidades = red.probabilidades(ventana_del_modelo(espectro, configuracion))
        en_motor = {d.grupo for d in completo.detecciones}
        en_reglas = {d.grupo for d in solo_reglas.detecciones}
        for g, p in zip(grupos, probabilidades):
            reales[g].append(fila[g])
            ml[g].append(p >= 0.5)
            motor[g].append(g in en_motor)
            reglas[g].append(g in en_reglas)

    r_ml = {g: metricas(reales[g], ml[g]) for g in grupos}
    r_motor = {g: metricas(reales[g], motor[g]) for g in grupos}
    r_reglas = {g: metricas(reales[g], reglas[g]) for g in grupos}
    r_trivial = {g: metricas(reales[g], [True] * len(reales[g])) for g in grupos}

    def veredicto(resultados: dict[str, dict]) -> list[str]:
        salida = []
        for g in PUERTA:
            m = resultados[g]
            if m["support"] < SUPPORT_MINIMO:
                estado = f"sin decidir (support {m['support']} < {SUPPORT_MINIMO})"
            else:
                estado = "pasa" if m["f1"] >= F1_PUERTA else "no pasa"
            salida.append(f"- {g} {nombres[g]}: F1 {m['f1']:.3f}, {estado}")
        return salida

    descripcion = red.descripcion
    texto_split = SPLIT_PRUEBA.read_bytes()
    lineas = [
        "# RNF-08 · evaluación de la vía ML y del motor completo (T-16d)",
        "",
        f"Corrida única el {date.today():%d/%m/%Y} con `python -m herramientas.entrenamiento.evaluar`.",
        "",
        "| | |",
        "|---|---|",
        f"| Conjunto de prueba | {len(filas)} espectros de {len(texto_split.splitlines())} compuestos (Chemotion IR) |",
        f"| SHA-256 de `split-prueba.txt` | `{hashlib.sha256(texto_split).hexdigest()}` |",
        f"| Semilla del entrenamiento | {descripcion['semilla']} |",
        f"| Época elegida (por validación) | {descripcion['epoca_elegida']} |",
        f"| Umbral del motor (UT-03) | {round(umbral * 100)} % |",
        f"| Pesos de la fusión (UT-03) | reglas {configuracion.motor.peso_reglas}, ML {configuracion.motor.peso_ml} |",
        f"| Etiquetado | {descripcion['etiquetado']} |",
        f"| Support mínimo para decidir | {SUPPORT_MINIMO} positivos (PROVISIONAL) |",
        f"| Tiempo del motor completo por espectro | promedio {1000 * sum(tiempos) / len(tiempos):.0f} ms, máximo {1000 * max(tiempos):.0f} ms (RNF-02 pide menos de 5 s) |",
        "",
        "Las celdas enmascaradas (la x de `conjunto.csv`) no cuentan en ninguna tabla.",
        "",
        "## Puerta de D-13 (F1 de al menos 0.80 en GF-01, GF-04 y GF-05)",
        "",
        "**Vía ML sola:**",
        "",
        *veredicto(r_ml),
        "",
        "**Motor completo:**",
        "",
        *veredicto(r_motor),
        "",
        "## Tablas",
        "",
        *tabla("1. Vía ML sola, corte en 0.5", r_ml, grupos, nombres),
        *tabla(f"2. Motor completo, fusión y umbral de {round(umbral * 100)} %", r_motor, grupos, nombres),
        *tabla("3. Vía de reglas sola, mismo umbral (contexto)", r_reglas, grupos, nombres),
        *tabla("4. Predictor que siempre dice que sí (contexto)", r_trivial, grupos, nombres),
    ]
    EVIDENCIA.write_text("\n".join(lineas), encoding="utf-8")
    print("\n".join(lineas))


if __name__ == "__main__":
    main()
