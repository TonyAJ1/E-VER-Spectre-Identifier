"""Espectros simulados para probar MOD-06 sin datos reales.

Cada espectro se arma sumando bandas gaussianas sobre la rejilla de UT-03, ya
en absorbancia y normalizado de 0 a 1, que es exactamente lo que MOD-06 recibe
de MOD-04. No pretenden ser espectros reales: solo ponen bandas donde la
prueba las necesita. Se generan en el momento y no se guardan.
"""

from __future__ import annotations

import math
import random

from backend.preprocesamiento.rejilla import eje as eje_de_rejilla
from backend.utilerias.configuracion import obtener as obtener_configuracion


def eje() -> list[float]:
    procesamiento = obtener_configuracion().procesamiento
    return eje_de_rejilla(procesamiento.puntos_rejilla, procesamiento.rango_rejilla_cm1)


def espectro(bandas, *, ruido: float = 0.0, semilla: int = 7):
    """bandas es una lista de (centro, altura, ancho a media altura en cm⁻¹)."""
    ondas = eje()
    azar = random.Random(semilla)
    valores = []
    for onda in ondas:
        total = 0.0
        for centro, altura, ancho in bandas:
            sigma = ancho / 2.3548
            total += altura * math.exp(-((onda - centro) ** 2) / (2 * sigma**2))
        if ruido:
            total += azar.gauss(0, ruido)
        valores.append(total)
    menor, mayor = min(valores), max(valores)
    return ondas, [(v - menor) / (mayor - menor) for v in valores]


CETONA = [(1715, 1.0, 25), (2965, 0.25, 30), (1360, 0.5, 20), (1220, 0.6, 30)]
ALCOHOL = [(3350, 0.8, 300), (2950, 0.5, 40), (1050, 1.0, 40)]
AMINA = [(3360, 0.35, 35), (3440, 0.3, 35), (2930, 0.4, 40), (1620, 0.5, 30)]
NITRILO = [(2250, 0.45, 20), (2950, 0.4, 40), (1450, 0.6, 25)]
ALQUENO = [(1645, 0.3, 20), (3080, 0.2, 20), (2950, 0.5, 40), (910, 1.0, 20)]
AROMATICO = [(1600, 0.35, 15), (1500, 0.4, 15), (3040, 0.15, 25), (700, 1.0, 20)]
ACIDO_AROMATICO = [
    (3000, 0.45, 500),
    (1690, 1.0, 30),
    (1600, 0.4, 15),
    (1500, 0.3, 15),
    (3070, 0.15, 20),
    (1290, 0.7, 30),
]
