"""T-16c: entrena la CNN 1D de la vía ML.

    python -m herramientas.entrenamiento.entrenar

Necesita PyTorch (herramientas/entrenamiento/requisitos.txt) y lo que deja
T-16a-2: datos/dataset/conjunto.csv y datos/dataset/vectores.npz. Escribe el
archivo de pesos en motor_identificacion/modelo/red.npz, que la aplicación lee
con NumPy (motor_identificacion/inferencia/red.py).

Lo que fija el plan (T-16c) y cómo se cumple:

- Salida sigmoide de siete probabilidades independientes: la pérdida es
  entropía cruzada binaria por grupo.
- Semilla fija y registrada: SEMILLA, escrita también dentro del archivo de
  pesos.
- Desbalance de clases atendido: cada grupo pesa sus positivos según
  negativos entre positivos del conjunto de entrenamiento, con un tope.
- Celdas enmascaradas (la x de conjunto.csv): pesan cero en la pérdida.
- Aumentación (opción C de D-12) solo sobre el conjunto de entrenamiento:
  ruido, inclinación de la línea base, corrimiento de unos puntos y escala.
- Se elige la época con menor pérdida en validación. El conjunto de prueba no
  se abre aquí: es de T-16d y se usa una sola vez.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys

import numpy as np
import torch
from torch import nn

from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.dataset.etiquetar import CONJUNTO, ENMASCARADA, SPLIT_PRUEBA, VECTORES
from motor_identificacion.inferencia.red import ARCHIVO_PESOS, CONVOLUCIONES, cargar_red

SEMILLA = 20261124
EPOCAS = 120
PACIENCIA = 20
LOTE = 64
TASA = 1e-3
DECAIMIENTO = 1e-4
TOPE_PESO_POSITIVO = 10.0

#: Las capas: canales de salida y ancho del filtro. El relleno de cada una
#: está en CONVOLUCIONES de red.py, para que las dos copias no se separen.
CANALES = (16, 32, 64, 64)
ANCHOS = (11, 9, 7, 5)
OCULTAS = 64
ABANDONO = 0.3

#: Aumentación, en las unidades del vector normalizado (0 a 1).
RUIDO = 0.005
PENDIENTE = 0.03
CORRIMIENTO = 3
ESCALA = 0.1


def fijar_semilla(semilla: int = SEMILLA) -> None:
    random.seed(semilla)
    np.random.seed(semilla)
    torch.manual_seed(semilla)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(4)


class Red(nn.Module):
    """La misma red que motor_identificacion/inferencia/red.py."""

    def __init__(self, largo: int, grupos: int) -> None:
        super().__init__()
        entrada = 1
        for (nombre, relleno), canales, ancho in zip(CONVOLUCIONES, CANALES, ANCHOS):
            setattr(self, nombre, nn.Conv1d(entrada, canales, ancho, padding=relleno))
            entrada = canales
            largo = (largo + 2 * relleno - ancho + 1) // 2
        self.d1 = nn.Linear(entrada * largo, OCULTAS)
        self.d2 = nn.Linear(OCULTAS, grupos)
        self.abandono = nn.Dropout(ABANDONO)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.unsqueeze(1)
        for nombre, _ in CONVOLUCIONES:
            x = nn.functional.max_pool1d(torch.relu(getattr(self, nombre)(x)), 2)
        x = self.abandono(x.flatten(1))
        x = self.abandono(torch.relu(self.d1(x)))
        return self.d2(x)


def cargar_conjunto(grupos: list[str]) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Vectores, etiquetas y máscara de cada conjunto."""
    guardado = np.load(VECTORES, allow_pickle=False)
    posicion = {a: i for i, a in enumerate(guardado["archivos"])}
    matriz = guardado["vectores"]
    partes: dict[str, list] = {}
    with CONJUNTO.open(encoding="utf-8", newline="") as flujo:
        for fila in csv.DictReader(flujo):
            celdas = [fila[g] for g in grupos]
            etiqueta = [1.0 if c == "1" else 0.0 for c in celdas]
            mascara = [0.0 if c == ENMASCARADA else 1.0 for c in celdas]
            partes.setdefault(fila["split"], []).append(
                (matriz[posicion[fila["archivo"]]], etiqueta, mascara)
            )
    return {
        nombre: tuple(np.asarray(columna, dtype=np.float32) for columna in zip(*filas))
        for nombre, filas in partes.items()
    }


def aumentar(x: torch.Tensor, azar: torch.Generator) -> torch.Tensor:
    """Variantes creíbles del mismo espectro; la química no cambia."""
    n, largo = x.shape
    rampa = torch.linspace(-1.0, 1.0, largo)
    pendiente = (torch.rand(n, 1, generator=azar) * 2 - 1) * PENDIENTE
    escala = 1 + (torch.rand(n, 1, generator=azar) * 2 - 1) * ESCALA
    ruido = torch.randn(n, largo, generator=azar) * RUIDO
    corrido = torch.empty_like(x)
    pasos = torch.randint(-CORRIMIENTO, CORRIMIENTO + 1, (n,), generator=azar)
    for i, paso in enumerate(pasos.tolist()):
        if paso > 0:
            corrido[i, paso:] = x[i, :-paso]
            corrido[i, :paso] = x[i, 0]
        elif paso < 0:
            corrido[i, :paso] = x[i, -paso:]
            corrido[i, paso:] = x[i, -1]
        else:
            corrido[i] = x[i]
    return corrido * escala + pendiente * rampa + ruido


def perdida(logits, etiqueta, mascara, peso_positivo) -> torch.Tensor:
    por_celda = nn.functional.binary_cross_entropy_with_logits(
        logits, etiqueta, pos_weight=peso_positivo, reduction="none"
    )
    return (por_celda * mascara).sum() / mascara.sum().clamp(min=1)


def f1_por_grupo(prob: np.ndarray, etiqueta: np.ndarray, mascara: np.ndarray, corte=0.5):
    salida = []
    for j in range(etiqueta.shape[1]):
        m = mascara[:, j] > 0
        y, p = etiqueta[m, j] > 0.5, prob[m, j] >= corte
        vp, fp, fn = int((y & p).sum()), int((~y & p).sum()), int((y & ~p).sum())
        salida.append(2 * vp / max(2 * vp + fp + fn, 1))
    return salida


def main() -> None:
    fijar_semilla()
    grupos = [g.id for g in obtener_catalogo().grupos]
    configuracion = obtener_configuracion()
    datos = cargar_conjunto(grupos)
    x_ent, y_ent, m_ent = (torch.from_numpy(a) for a in datos["entrenamiento"])
    x_val, y_val, m_val = (torch.from_numpy(a) for a in datos["validacion"])
    largo = x_ent.shape[1]
    print(f"entrenamiento {len(x_ent)}, validación {len(x_val)}, ventana de {largo} puntos")

    positivos = (y_ent * m_ent).sum(0)
    negativos = ((1 - y_ent) * m_ent).sum(0)
    peso_positivo = (negativos / positivos.clamp(min=1)).clamp(1.0, TOPE_PESO_POSITIVO)
    print("peso de los positivos:", {g: round(float(p), 2) for g, p in zip(grupos, peso_positivo)})

    red = Red(largo, len(grupos))
    optimizador = torch.optim.Adam(red.parameters(), lr=TASA, weight_decay=DECAIMIENTO)
    azar = torch.Generator().manual_seed(SEMILLA)

    mejor, mejor_epoca, estado = float("inf"), -1, None
    for epoca in range(1, EPOCAS + 1):
        red.train()
        orden = torch.randperm(len(x_ent), generator=azar)
        for inicio in range(0, len(orden), LOTE):
            i = orden[inicio : inicio + LOTE]
            optimizador.zero_grad()
            salida = red(aumentar(x_ent[i], azar))
            perdida(salida, y_ent[i], m_ent[i], peso_positivo).backward()
            optimizador.step()
        red.eval()
        with torch.no_grad():
            val = float(perdida(red(x_val), y_val, m_val, peso_positivo))
        if val < mejor:
            mejor, mejor_epoca = val, epoca
            estado = {k: v.detach().clone() for k, v in red.state_dict().items()}
        if epoca % 10 == 0:
            print(f"época {epoca:3d}  pérdida en validación {val:.4f}  (mejor {mejor:.4f} en {mejor_epoca})")
            sys.stdout.flush()
        if epoca - mejor_epoca >= PACIENCIA:
            print(f"se detiene en la época {epoca}: {PACIENCIA} épocas sin mejorar")
            break

    red.load_state_dict(estado)
    red.eval()
    with torch.no_grad():
        prob_val = torch.sigmoid(red(x_val)).numpy()
    f1 = f1_por_grupo(prob_val, y_val.numpy(), m_val.numpy())
    print(f"\nF1 en validación (corte 0.5), época {mejor_epoca}:")
    for g, valor in zip(grupos, f1):
        print(f"  {g}: {valor:.3f}")

    descripcion = {
        "tarea": "T-16c",
        "arquitectura": "CNN 1D, 4 convoluciones con ReLU y reducción, 2 densas, salida sigmoide",
        "grupos": grupos,
        "puntos_rejilla": configuracion.procesamiento.puntos_rejilla,
        "largo_ventana": largo,
        "rango_ventana_cm1": list(configuracion.validacion.rango_requerido_cm1),
        "semilla": SEMILLA,
        "epoca_elegida": mejor_epoca,
        "perdida_validacion": round(mejor, 5),
        "f1_validacion": {g: round(v, 4) for g, v in zip(grupos, f1)},
        "split_prueba_sha256": hashlib.sha256(SPLIT_PRUEBA.read_bytes()).hexdigest(),
        "datos": "Chemotion IR, DOI 10.22000/OGoEQGlsZGElrgst, CC BY-SA 4.0",
        "etiquetado": "D-24 v2 provisional (ver herramientas/dataset/etiquetar.py)",
        "torch": torch.__version__,
    }
    pesos = {k: v.numpy() for k, v in estado.items()}
    ARCHIVO_PESOS.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ARCHIVO_PESOS, descripcion=np.asarray(json.dumps(descripcion)), **pesos)

    # La copia de NumPy tiene que dar lo mismo que PyTorch.
    copia = cargar_red(ARCHIVO_PESOS, tuple(grupos))
    diferencia = max(
        float(np.abs(np.asarray(copia.probabilidades(tuple(v))) - p).max())
        for v, p in zip(x_val[:50].numpy(), prob_val[:50])
    )
    print(f"\nguardado en {ARCHIVO_PESOS.relative_to(ARCHIVO_PESOS.parents[2])}")
    print(f"diferencia máxima entre PyTorch y NumPy: {diferencia:.2e}")
    if diferencia > 1e-4:
        raise SystemExit("la copia de NumPy no reproduce la red")


if __name__ == "__main__":
    main()
