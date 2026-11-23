"""Pruebas de T-22: un grupo detectado sin plantilla de explicación.

CA-07.3 pide que el grupo aparezca con «Explicación no disponible», que el
error se registre y que el resto de los resultados se muestre normalmente.
"""

from __future__ import annotations

import logging

from backend.api.analisis import analizar_espectro
from backend.educativo.explicador import explicar
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.catalogo import obtener_plantillas
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.pruebas import espectros_simulados as sim


def _sin(grupo: str) -> dict:
    return {k: v for k, v in obtener_plantillas().items() if k != grupo}


def prueba_ca_07_3_sin_plantilla_dice_explicacion_no_disponible(caplog) -> None:
    deteccion = {"grupo": "GF-05", "region_cm1": [1670.0, 1780.0], "pico_cm1": 1715.0}

    with caplog.at_level(logging.ERROR):
        explicacion = explicar(deteccion, obtener_catalogo(), _sin("GF-05"))

    assert explicacion == {"disponible": False, "aviso": "Explicación no disponible"}
    assert any("GF-05" in r.getMessage() for r in caplog.records)


def prueba_ca_07_3_los_demas_grupos_se_explican_normalmente() -> None:
    eje, intensidad = sim.espectro(sim.CETONA)

    resultado = analizar_espectro(
        eje, intensidad, obtener_configuracion(), obtener_catalogo(), _sin("GF-05")
    )

    por_grupo = {d["grupo"]: d for d in resultado["detecciones"]}
    assert por_grupo["GF-05"]["explicacion"]["disponible"] is False
    assert por_grupo["GF-05"]["porcentaje"] >= 60
    assert por_grupo["GF-03"]["explicacion"]["disponible"] is True
