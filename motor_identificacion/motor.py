"""Punto de entrada de MOD-06.

Corre la vía de reglas, la de aprendizaje automático si su peso no es cero, y
fusiona las dos. Si UT-03 pide usar el modelo y el modelo no existe, el motor
falla con ModeloNoDisponible en lugar de inventar probabilidades; quien lo
llama lo traduce al mensaje de fallo de UT-02.
"""

from __future__ import annotations

from typing import Any

from motor_identificacion.inferencia.fusion import fusionar
from motor_identificacion.modelo.via_ml import ModeloNoDisponible, ViaML
from motor_identificacion.reglas.via_reglas import evaluar

__all__ = ["ModeloNoDisponible", "identificar"]

_via_ml: ViaML | None = None


def _modelo() -> ViaML:
    """El modelo se carga una sola vez en memoria, como pide el diseño."""
    global _via_ml
    if _via_ml is None:
        _via_ml = ViaML()
    return _via_ml


def identificar(
    eje: list[float],
    intensidad: list[float],
    grupos,
    *,
    umbral: float,
    peso_reglas: float,
    peso_ml: float,
    via_ml: ViaML | None = None,
) -> dict[str, Any]:
    if len(eje) != len(intensidad) or len(eje) < 3:
        raise ValueError("el eje y la intensidad tienen que tener el mismo tamaño")

    evaluaciones = evaluar(eje, intensidad, grupos)

    probabilidades = None
    if peso_ml > 0:
        probabilidades = (via_ml or _modelo()).predecir(eje, intensidad)

    return fusionar(
        evaluaciones,
        probabilidades,
        grupos,
        umbral=umbral,
        peso_reglas=peso_reglas,
        peso_ml=peso_ml,
    )
