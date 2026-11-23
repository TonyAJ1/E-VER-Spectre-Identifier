"""Vía de aprendizaje automático de MOD-06 (tarea T-16, en plan B).

El diseño pide una red convolucional de una dimensión que reciba el mismo
vector que deja MOD-04 y devuelva una probabilidad por cada uno de los 7
grupos. Para entrenarla hacen falta espectros reales etiquetados de SDBS o
NIST, separados en entrenamiento, validación y prueba sin repetir compuestos.
Ese conjunto todavía no existe, así que el modelo no se ha entrenado y no hay
pesos.

Mientras tanto aplica el plan B del diseño de MOD-06 (sección 10): UT-03 pone
el peso de esta vía en cero y el motor trabaja solo con reglas, sin cambiar el
contrato. Esta clase deja lista la puerta: cuando exista el modelo, se carga
aquí una sola vez y predecir devuelve las probabilidades.
"""

from __future__ import annotations

from pathlib import Path

CARPETA_MODELO = Path(__file__).resolve().parent

#: Nombre que tendrá el archivo de pesos cuando el equipo entrene el modelo.
ARCHIVO_PESOS = "pesos_cnn1d.bin"


class ModeloNoDisponible(Exception):
    """Se pidió una predicción y no hay modelo entrenado."""


class ViaML:
    def __init__(self, carpeta: Path = CARPETA_MODELO) -> None:
        self.ruta_pesos = carpeta / ARCHIVO_PESOS
        # Aunque aparezca un archivo de pesos, la vía sigue apagada hasta que
        # exista el código que lo carga y sus métricas de RNF-08.
        self.disponible = False

    def predecir(self, eje: list[float], intensidad: list[float]) -> dict[str, float]:
        """Probabilidad por grupo. Hoy siempre avisa que no hay modelo."""
        raise ModeloNoDisponible(
            "la vía de aprendizaje automático no tiene un modelo entrenado"
        )
