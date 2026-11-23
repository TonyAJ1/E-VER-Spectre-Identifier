"""Explicación de cada grupo detectado (tarea T-21).

Junta cuatro piezas, que son las que pide RF-06: la región característica del
grupo, la posición del pico que se observó, el rasgo que lo delata y por qué
ese pico corresponde al grupo. La región y el rasgo salen del catálogo de
UT-01, la posición sale del motor y el porqué sale de la plantilla. Así los
números viven en un solo lugar.
"""

from __future__ import annotations

from typing import Any

from backend.utilerias.catalogo import Catalogo, Plantilla

UNIDAD = "cm⁻¹"


def _numero(valor: float) -> str:
    return f"{valor:g}"


def texto_region(region: list[float] | tuple[float, float]) -> str:
    return f"de {_numero(region[0])} a {_numero(region[1])} {UNIDAD}"


def explicar(
    deteccion: dict[str, Any],
    catalogo: Catalogo,
    plantillas: dict[str, Plantilla],
) -> dict[str, Any]:
    grupo = catalogo.grupo(deteccion["grupo"])
    plantilla = plantillas[deteccion["grupo"]]
    pico = deteccion.get("pico_cm1")
    return {
        "disponible": True,
        "region": texto_region(deteccion["region_cm1"]),
        "posicion": f"{_numero(pico)} {UNIDAD}" if pico is not None else None,
        "rasgo": grupo.rasgo,
        "por_que": plantilla.por_que,
    }
