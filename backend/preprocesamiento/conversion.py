"""Orden de los puntos y paso a absorbancia, en MOD-04 (tarea T-09).

Los archivos pueden traer el eje de 400 a 4000 o de 4000 a 400, y la
intensidad en absorbancia o en transmitancia, en fracción o en porcentaje.
Aquí todo termina igual: puntos ordenados de menor a mayor número de onda e
intensidad en absorbancia. Así CA-03.2 se cumple por construcción, porque un
archivo al revés queda idéntico a uno al derecho.

La conversión es la de los Requerimientos: A = menos el logaritmo en base 10
de T, con T en fracción.
"""

from __future__ import annotations

import math
from statistics import median

from backend.preprocesamiento.lector import ABSORBANCIA, DESCONOCIDA, TRANSMITANCIA

#: Transmitancia expresada en por ciento, de 0 a 100.
PORCENTAJE = "porcentaje"

#: Si algún valor de transmitancia pasa de este número, se entiende que viene
#: en porcentaje. Una transmitancia en fracción no llega a 1.5 ni con ruido.
#: Es un SUPUESTO registrado en docs/plan/incremento-2.md.
LIMITE_PORCENTAJE = 1.5

#: Un CSV sin encabezado con todos sus valores entre 0 y 1 puede ser
#: transmitancia en fracción o absorbancia baja. Se toma como transmitancia si
#: la mitad o más de sus valores pasan de este número, porque la línea base de
#: un espectro en transmitancia está arriba y la de absorbancia está abajo.
#: También es un SUPUESTO.
MEDIANA_TRANSMITANCIA = 0.5

#: Una transmitancia de cero o negativa no tiene logaritmo. Se sube a este
#: valor antes de convertir para que el cálculo no falle.
TRANSMITANCIA_MINIMA = 1e-6


def ordenar(pares) -> list[tuple[float, float]]:
    """Ordena de menor a mayor número de onda.

    Si un número de onda aparece dos veces, se queda uno solo con el promedio
    de sus intensidades. La interpolación de T-10 necesita un eje que siempre
    crezca.
    """
    agrupados: dict[float, list[float]] = {}
    for onda, intensidad in pares:
        agrupados.setdefault(onda, []).append(intensidad)
    return [
        (onda, sum(valores) / len(valores))
        for onda, valores in sorted(agrupados.items())
    ]


def unidad_efectiva(intensidades: list[float], unidad: str) -> str:
    """Decide si las intensidades son absorbancia o transmitancia en fracción o
    en porcentaje. Devuelve absorbancia, transmitancia o porcentaje."""
    maximo = max(intensidades)
    if unidad == ABSORBANCIA:
        return ABSORBANCIA
    if unidad == TRANSMITANCIA:
        return PORCENTAJE if maximo > LIMITE_PORCENTAJE else TRANSMITANCIA
    if unidad == DESCONOCIDA:
        if maximo > LIMITE_PORCENTAJE:
            return PORCENTAJE
        if min(intensidades) >= 0 and median(intensidades) > MEDIANA_TRANSMITANCIA:
            return TRANSMITANCIA
        return ABSORBANCIA
    raise ValueError(f"unidad desconocida para MOD-04: {unidad}")


def a_absorbancia(intensidades: list[float], unidad: str) -> list[float]:
    """Pasa las intensidades a absorbancia según su unidad efectiva."""
    efectiva = unidad_efectiva(intensidades, unidad)
    if efectiva == ABSORBANCIA:
        return list(intensidades)
    divisor = 100.0 if efectiva == PORCENTAJE else 1.0
    return [
        -math.log10(max(valor / divisor, TRANSMITANCIA_MINIMA))
        for valor in intensidades
    ]
