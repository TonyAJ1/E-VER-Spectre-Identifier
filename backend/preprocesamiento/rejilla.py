"""Normalización y rejilla fija de MOD-04 (tarea T-10).

Este es el contrato que después usan MOD-05 para la gráfica y MOD-06 para el
motor. Todo espectro sale con el mismo número de puntos, con el eje de mayor a
menor número de onda como se acostumbra en infrarrojo, y con la intensidad
entre 0 y 1. El número de puntos y el rango del eje se leen de UT-03.

Fuera del tramo que de verdad midió el archivo no hay datos. Ahí la
intensidad queda en cero, que después de normalizar significa sin absorción,
y el resultado dice cuál fue el tramo medido para que la gráfica no dibuje
valores que nadie midió.
"""

from __future__ import annotations

from bisect import bisect_left


def eje(puntos: int, rango: tuple[float, float]) -> list[float]:
    """El eje de la rejilla, del número de onda mayor al menor."""
    menor, mayor = rango
    paso = (mayor - menor) / (puntos - 1)
    valores = [mayor - indice * paso for indice in range(puntos)]
    valores[-1] = menor  # evita que el redondeo deje el último punto corrido
    return valores


def remuestrear(
    ordenados: list[tuple[float, float]], eje_rejilla: list[float]
) -> tuple[list[float | None], tuple[float, float]]:
    """Interpola de forma lineal los puntos medidos sobre el eje de la rejilla.

    ordenados tiene que venir de menor a mayor número de onda y sin repetidos,
    que es como lo deja T-09. Devuelve un valor por punto del eje, o None si
    ese punto cae fuera de lo que se midió, y el tramo medido.
    """
    ondas = [onda for onda, _ in ordenados]
    intensidades = [intensidad for _, intensidad in ordenados]
    menor, mayor = ondas[0], ondas[-1]

    valores: list[float | None] = []
    for onda in eje_rejilla:
        if onda < menor or onda > mayor:
            valores.append(None)
            continue
        derecha = bisect_left(ondas, onda)
        if ondas[derecha] == onda:
            valores.append(intensidades[derecha])
            continue
        izquierda = derecha - 1
        x0, x1 = ondas[izquierda], ondas[derecha]
        y0, y1 = intensidades[izquierda], intensidades[derecha]
        valores.append(y0 + (y1 - y0) * (onda - x0) / (x1 - x0))
    return valores, (menor, mayor)


#: Qué tan parecidos tienen que ser el valor más alto y el más bajo para
#: considerar que el espectro es una línea plana. Se mide en proporción al
#: tamaño de los valores, para que no dependa de la unidad.
TOLERANCIA_PLANO = 1e-9


def es_plano(valores: list[float | None]) -> bool:
    """Dice si los valores medidos son todos iguales (tarea T-11)."""
    medidos = [valor for valor in valores if valor is not None]
    minimo, maximo = min(medidos), max(medidos)
    escala = max(1.0, abs(minimo), abs(maximo))
    return maximo - minimo <= TOLERANCIA_PLANO * escala


def normalizar(valores: list[float | None]) -> list[float]:
    """Lleva los valores medidos a la escala de 0 a 1.

    El más bajo queda en 0 y el más alto en 1. Los puntos sin medición quedan
    en 0. Si todos los valores son iguales no hay forma de normalizar: el
    procesador lo revisa antes con es_plano, y si aun así llega aquí todo
    queda en cero en lugar de dividir entre cero.
    """
    medidos = [valor for valor in valores if valor is not None]
    minimo, maximo = min(medidos), max(medidos)
    amplitud = maximo - minimo
    if amplitud == 0:
        return [0.0 for _ in valores]
    return [
        0.0 if valor is None else (valor - minimo) / amplitud for valor in valores
    ]
