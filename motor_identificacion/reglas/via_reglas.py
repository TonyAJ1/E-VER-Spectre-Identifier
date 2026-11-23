"""Vía de reglas de MOD-06 (tarea T-15).

Para cada grupo del catálogo busca el pico que mejor cae en su región y le da
un puntaje entre 0 y 1. El puntaje es 1 cuando hay un pico claro dentro de la
región y baja con la distancia a la región, con la debilidad del pico, con una
forma que no es la esperada y con el ruido. Devuelve también la posición del
pico, que después usan la explicación y el resaltado.

El catálogo llega como objetos con los atributos de UT-01 (id, region_cm1,
regiones_de_busqueda y regla). Este módulo no importa el backend.
"""

from __future__ import annotations

from dataclasses import dataclass

from motor_identificacion.reglas.picos import Pico, a_orden_creciente, encontrar, ruido

#: Un pico un poco fuera de la región todavía cuenta, con menos puntaje. A
#: esta distancia, en cm⁻¹, el puntaje por posición ya es cero.
MARGEN_CM1 = 20.0

#: Cuántas veces el ruido tiene que superar la prominencia de un pico para
#: considerarlo claro. Por debajo el puntaje baja en proporción.
SENAL_SOBRE_RUIDO = 10.0

#: Sin su banda acompañante, un grupo que la necesita se queda con este
#: máximo, que está por debajo de cualquier umbral razonable.
SIN_ACOMPANANTE = 0.5


@dataclass(frozen=True)
class Evaluacion:
    grupo: str
    puntaje: float
    pico_cm1: float | None


def evaluar(eje: list[float], intensidad: list[float], grupos) -> list[Evaluacion]:
    """Puntaje de la vía de reglas para cada grupo del catálogo."""
    eje_creciente, valores = a_orden_creciente(eje, intensidad)
    picos = encontrar(eje_creciente, valores)
    nivel_de_ruido = ruido(valores)

    resultados = []
    for grupo in grupos:
        regla = grupo.regla
        puntaje, pico = _mejor(
            picos,
            grupo.regiones_de_busqueda(),
            regla.prominencia_referencia,
            nivel_de_ruido,
            regla.ancho_minimo_cm1,
            regla.ancho_maximo_cm1,
        )
        if regla.acompanante is not None and puntaje > 0:
            extra, _ = _mejor(
                picos,
                (regla.acompanante.region_cm1,),
                regla.acompanante.prominencia_referencia,
                nivel_de_ruido,
            )
            puntaje *= SIN_ACOMPANANTE + (1 - SIN_ACOMPANANTE) * extra
        resultados.append(
            Evaluacion(
                grupo=grupo.id,
                puntaje=round(puntaje, 4),
                pico_cm1=round(pico.posicion_cm1, 1) if pico and puntaje > 0 else None,
            )
        )
    return resultados


def _mejor(
    picos: list[Pico],
    regiones,
    referencia: float,
    nivel_de_ruido: float,
    ancho_minimo: float | None = None,
    ancho_maximo: float | None = None,
) -> tuple[float, Pico | None]:
    mejor_puntaje, mejor_pico = 0.0, None
    for pico in picos:
        posicion = max(_por_posicion(pico.posicion_cm1, region) for region in regiones)
        if posicion == 0:
            continue
        fuerza = min(1.0, pico.prominencia / referencia)
        claridad = (
            1.0
            if nivel_de_ruido == 0
            else min(1.0, pico.prominencia / (SENAL_SOBRE_RUIDO * nivel_de_ruido))
        )
        forma = _por_forma(pico.ancho_cm1, ancho_minimo, ancho_maximo)
        puntaje = posicion * fuerza * claridad * forma
        if puntaje > mejor_puntaje:
            mejor_puntaje, mejor_pico = puntaje, pico
    return mejor_puntaje, mejor_pico


def _por_posicion(onda: float, region: tuple[float, float]) -> float:
    menor, mayor = region
    if menor <= onda <= mayor:
        return 1.0
    distancia = menor - onda if onda < menor else onda - mayor
    return max(0.0, 1.0 - distancia / MARGEN_CM1)


def _por_forma(ancho: float, minimo: float | None, maximo: float | None) -> float:
    """Castiga una banda más angosta o más ancha de lo que pide el grupo.

    Se eleva al cuadrado para que una banda de la mitad del ancho esperado
    pierda tres cuartas partes del puntaje. Es lo que separa O–H de N–H.
    """
    if minimo is not None and ancho < minimo:
        return (ancho / minimo) ** 2
    if maximo is not None and ancho > maximo:
        return (maximo / ancho) ** 2
    return 1.0
