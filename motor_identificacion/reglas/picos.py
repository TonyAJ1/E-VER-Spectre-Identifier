"""Detección de picos para la vía de reglas (tarea T-15).

Trabaja sobre el espectro ya normalizado, en absorbancia de 0 a 1, así que un
pico es un máximo local. De cada pico se mide su prominencia, es decir cuánto
sobresale de lo que lo rodea, y su ancho a la mitad de esa prominencia, en
cm⁻¹. También se estima el ruido del espectro para no confundir ruido con
señal.

Todo está escrito en Python simple, sin librerías externas: con 1024 puntos
no hace falta más.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class Pico:
    posicion_cm1: float
    altura: float
    prominencia: float
    ancho_cm1: float


def a_orden_creciente(eje: list[float], valores: list[float]):
    """Devuelve eje y valores de menor a mayor número de onda."""
    if len(eje) > 1 and eje[0] > eje[-1]:
        return list(reversed(eje)), list(reversed(valores))
    return list(eje), list(valores)


def ruido(valores: list[float]) -> float:
    """Desviación estimada del ruido, a partir de la diferencia entre puntos
    vecinos. Usa la mediana para que los picos de verdad no la inflen."""
    diferencias = [abs(b - a) for a, b in zip(valores, valores[1:])]
    if not diferencias:
        return 0.0
    # 1.4826 convierte la mediana de desviaciones en una desviación estándar
    # y la raíz de 2 descuenta que cada diferencia mezcla el ruido de dos
    # puntos.
    return 1.4826 * median(diferencias) / 2**0.5


def encontrar(eje: list[float], valores: list[float]) -> list[Pico]:
    """Todos los máximos locales con su prominencia y su ancho.

    eje y valores tienen que venir de menor a mayor número de onda.
    """
    total = len(valores)
    picos: list[Pico] = []
    i = 1
    while i < total - 1:
        if valores[i] > valores[i - 1]:
            # Una meseta de valores iguales cuenta como un solo pico, en su
            # punto medio.
            j = i
            while j + 1 < total and valores[j + 1] == valores[i]:
                j += 1
            if j + 1 < total and valores[j + 1] < valores[i]:
                centro = (i + j) // 2
                picos.append(_medir(eje, valores, centro))
            i = j + 1
        else:
            i += 1
    return picos


def _medir(eje: list[float], valores: list[float], indice: int) -> Pico:
    altura = valores[indice]

    # Hacia cada lado se baja hasta encontrar un punto más alto que el pico o
    # el borde. Lo más bajo de ese tramo es la base de ese lado.
    base_izquierda = altura
    k = indice - 1
    while k >= 0 and valores[k] <= altura:
        base_izquierda = min(base_izquierda, valores[k])
        k -= 1
    base_derecha = altura
    k = indice + 1
    while k < len(valores) and valores[k] <= altura:
        base_derecha = min(base_derecha, valores[k])
        k += 1
    prominencia = altura - max(base_izquierda, base_derecha)

    nivel = altura - prominencia / 2
    izquierda = _cruce(eje, valores, indice, nivel, -1)
    derecha = _cruce(eje, valores, indice, nivel, 1)
    return Pico(
        posicion_cm1=eje[indice],
        altura=altura,
        prominencia=prominencia,
        ancho_cm1=derecha - izquierda,
    )


def _cruce(eje, valores, indice, nivel, paso) -> float:
    """Dónde la curva baja del nivel dado, caminando hacia un lado."""
    k = indice
    while 0 <= k + paso < len(valores) and valores[k + paso] > nivel:
        k += paso
    siguiente = k + paso
    if not 0 <= siguiente < len(valores):
        return eje[k]
    # Interpolación lineal entre el último punto arriba del nivel y el
    # primero abajo.
    y0, y1 = valores[k], valores[siguiente]
    if y0 == y1:
        return eje[siguiente]
    fraccion = (y0 - nivel) / (y0 - y1)
    return eje[k] + (eje[siguiente] - eje[k]) * fraccion
