"""La red neuronal de la vía ML (T-16c), lista para usarse en la aplicación.

La red se entrena con PyTorch (herramientas/entrenamiento/entrenar.py), pero
la aplicación no carga PyTorch: es una librería de casi un gigabyte y para
predecir solo hacen falta unas cuantas multiplicaciones. Por eso el
entrenamiento guarda los pesos en un archivo .npz y aquí se repite la misma
red con NumPy. La prueba de T-16c comprueba que las dos dan el mismo número.

La red es una CNN 1D de cuatro capas de convolución, cada una con ReLU y
reducción a la mitad, y después dos capas densas. La salida son siete
probabilidades independientes, una por grupo y en el orden de UT-01
(multi etiqueta, no multi clase).

El archivo de pesos guarda también la N de la rejilla con la que se entrenó
(D-19), el orden de los grupos y el largo de la ventana. Si alguno no cuadra
con la configuración y el catálogo, la red no se carga y la aplicación sigue
solo con reglas, como pide D-16.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

#: Dónde vive el archivo de pesos (D-18).
CARPETA_MODELO = Path(__file__).resolve().parents[1] / "modelo"
ARCHIVO_PESOS = CARPETA_MODELO / "red.npz"

#: Las capas de convolución: (nombre de los pesos, relleno). Cada una va
#: seguida de ReLU y de una reducción por máximo de tamaño 2.
CONVOLUCIONES = (("c1", 5), ("c2", 4), ("c3", 3), ("c4", 2))


class ErrorDeModelo(Exception):
    """El archivo de pesos no existe o no corresponde a esta aplicación."""


def _convolucion(x: np.ndarray, pesos: np.ndarray, sesgo: np.ndarray, relleno: int) -> np.ndarray:
    """Convolución 1D igual a la de PyTorch. x: (canales, largo)."""
    salida_canales, entrada_canales, ancho = pesos.shape
    x = np.pad(x, ((0, 0), (relleno, relleno)))
    largo = x.shape[1] - ancho + 1
    ventanas = np.lib.stride_tricks.sliding_window_view(x, ancho, axis=1)
    # ventanas: (entrada_canales, largo, ancho)
    return np.einsum("clk,ock->ol", ventanas[:, :largo, :], pesos) + sesgo[:, None]


def _reducir(x: np.ndarray) -> np.ndarray:
    """Máximo de cada par de puntos, descartando el último si sobra."""
    largo = x.shape[1] // 2
    return x[:, : largo * 2].reshape(x.shape[0], largo, 2).max(axis=2)


def _sigmoide(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


@dataclass(frozen=True)
class RedEntrenada:
    """Cumple el protocolo ModeloML de la fusión."""

    puntos_rejilla: int
    largo_ventana: int
    grupos: tuple[str, ...]
    pesos: dict[str, np.ndarray]
    descripcion: dict

    def logits(self, ventana: tuple[float, ...]) -> np.ndarray:
        if len(ventana) != self.largo_ventana:
            raise ErrorDeModelo(
                f"la ventana tiene {len(ventana)} puntos y la red espera {self.largo_ventana}"
            )
        x = np.asarray(ventana, dtype=np.float32)[None, :]
        for nombre, relleno in CONVOLUCIONES:
            x = _convolucion(x, self.pesos[f"{nombre}.weight"], self.pesos[f"{nombre}.bias"], relleno)
            x = _reducir(np.maximum(x, 0.0))
        x = x.reshape(-1)
        x = np.maximum(self.pesos["d1.weight"] @ x + self.pesos["d1.bias"], 0.0)
        return self.pesos["d2.weight"] @ x + self.pesos["d2.bias"]

    def probabilidades(self, ventana: tuple[float, ...]) -> tuple[float, ...]:
        return tuple(float(p) for p in _sigmoide(self.logits(ventana)))


def cargar_red(
    ruta: Path = ARCHIVO_PESOS, grupos_esperados: tuple[str, ...] | None = None
) -> RedEntrenada:
    """Lee el archivo de pesos y comprueba que está completo.

    Raises:
        ErrorDeModelo: si el archivo no existe, le falta algo o los grupos no
            están en el orden del catálogo.
    """
    if not ruta.is_file():
        raise ErrorDeModelo(f"no existe {ruta.name}")
    with np.load(ruta, allow_pickle=False) as archivo:
        datos = {clave: archivo[clave] for clave in archivo.files}
    try:
        descripcion = json.loads(str(datos.pop("descripcion")))
        grupos = tuple(descripcion["grupos"])
        red = RedEntrenada(
            puntos_rejilla=int(descripcion["puntos_rejilla"]),
            largo_ventana=int(descripcion["largo_ventana"]),
            grupos=grupos,
            pesos={k: v.astype(np.float32) for k, v in datos.items()},
            descripcion=descripcion,
        )
    except (KeyError, ValueError, TypeError) as error:
        raise ErrorDeModelo(f"el archivo de pesos está incompleto: {error}") from error
    faltan = {f"{n}.{p}" for n, _ in CONVOLUCIONES for p in ("weight", "bias")}
    faltan |= {"d1.weight", "d1.bias", "d2.weight", "d2.bias"}
    faltan -= set(red.pesos)
    if faltan:
        raise ErrorDeModelo(f"faltan pesos: {sorted(faltan)}")
    if grupos_esperados is not None and grupos != tuple(grupos_esperados):
        raise ErrorDeModelo("los grupos de la red no están en el orden del catálogo")
    return red
