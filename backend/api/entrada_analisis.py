"""Revisión de lo que llega a POST /api/analizar (D-17).

La página manda en JSON el mismo objeto espectro que recibió de
POST /api/procesar. Como viene del navegador, alguien podría mandar cualquier
cosa, así que antes de tocar el motor se revisa que tenga la forma del
contrato de MOD-04 a MOD-06:

1. El eje tiene los puntos de la rejilla de UT-03 y va de 4000 a 400 cm⁻¹ en
   pasos parejos, con la misma tolerancia de seis decimales con que viaja.
2. La intensidad tiene la misma longitud y cada valor es un número entre 0 y 1.
3. El tramo medido son dos números, el menor primero, que se cruzan con la
   rejilla. Puede salirse de ella: es lo que de verdad cubría el archivo, y
   muchos equipos miden desde menos de 400 cm⁻¹.

Si algo no cuadra se devuelve None y la ruta responde ESPECTRO_INVALIDO. Aquí
no se redacta ningún mensaje.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from backend.utilerias.configuracion import Configuracion

#: Cuánto puede separarse un punto del eje de la rejilla esperada. El eje
#: viaja redondeado a seis decimales, así que un poco más que eso basta.
TOLERANCIA_EJE_CM1: float = 1e-4


@dataclass(frozen=True)
class EspectroRecibido:
    """El espectro ya revisado, con la forma que el motor espera."""

    eje_cm1: tuple[float, ...]
    intensidad: tuple[float, ...]
    rango_medido_cm1: tuple[float, float]


def _numero(valor: Any) -> float | None:
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    numero = float(valor)
    return numero if math.isfinite(numero) else None


def _lista_de_numeros(valor: Any) -> tuple[float, ...] | None:
    if not isinstance(valor, list):
        return None
    numeros = tuple(_numero(v) for v in valor)
    if any(n is None for n in numeros):
        return None
    return numeros  # type: ignore[return-value]


def espectro_desde(cuerpo: Any, configuracion: Configuracion) -> EspectroRecibido | None:
    """El espectro del cuerpo de la petición, o None si no tiene la forma.

    Args:
        cuerpo: el JSON ya leído. Se acepta el objeto espectro directo o
            envuelto en una llave espectro, como lo responde /api/procesar.
        configuracion: UT-03, de donde salen la rejilla y su rango.
    """
    if isinstance(cuerpo, dict) and isinstance(cuerpo.get("espectro"), dict):
        cuerpo = cuerpo["espectro"]
    if not isinstance(cuerpo, dict):
        return None

    eje = _lista_de_numeros(cuerpo.get("eje_cm1"))
    intensidad = _lista_de_numeros(cuerpo.get("intensidad"))
    medido = _lista_de_numeros(cuerpo.get("rango_medido_cm1"))
    if eje is None or intensidad is None or medido is None:
        return None

    puntos = configuracion.procesamiento.puntos_rejilla
    minimo, maximo = configuracion.procesamiento.rango_rejilla_cm1
    if len(eje) != puntos or len(intensidad) != puntos or len(medido) != 2:
        return None

    paso = (maximo - minimo) / (puntos - 1)
    for i, onda in enumerate(eje):
        if abs(onda - (maximo - paso * i)) > TOLERANCIA_EJE_CM1:
            return None

    if any(not 0 <= valor <= 1 for valor in intensidad):
        return None

    menor, mayor = medido
    if not (menor < mayor and menor < maximo and mayor > minimo):
        return None

    return EspectroRecibido(eje, intensidad, (menor, mayor))
