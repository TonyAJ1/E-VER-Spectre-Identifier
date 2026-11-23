"""Pruebas de T-17: fusión de las dos vías y umbral de 60 %.

CA-05.3 pide que un grupo con exactamente 60 % aparezca como detectado y uno
con 59 % no. El umbral y los pesos se leen de UT-03. También se revisa que
con el peso del modelo en cero el motor siga funcionando (plan B), que
coincidir las dos vías suba la confianza y discrepar la baje, y que el
resultado siga el contrato de la sección 5 del diseño de MOD-06.
"""

from __future__ import annotations

import pytest

from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.inferencia.fusion import confianza, fusionar
from motor_identificacion.modelo.via_ml import ModeloNoDisponible, ViaML
from motor_identificacion.motor import identificar
from motor_identificacion.pruebas import espectros_simulados as sim
from motor_identificacion.reglas.via_reglas import Evaluacion


def _motor():
    return obtener_configuracion().motor


def _fusionar(evaluaciones, ml=None, peso_reglas=None, peso_ml=None):
    motor = _motor()
    return fusionar(
        evaluaciones,
        ml,
        obtener_catalogo().grupos,
        umbral=motor.umbral_confianza,
        peso_reglas=motor.peso_reglas if peso_reglas is None else peso_reglas,
        peso_ml=motor.peso_ml if peso_ml is None else peso_ml,
    )


def prueba_ca_05_3_con_60_aparece_y_con_59_no() -> None:
    umbral = _motor().umbral_confianza
    evaluaciones = [
        Evaluacion("GF-05", umbral, 1715.0),
        Evaluacion("GF-03", round(umbral - 0.01, 4), 2950.0),
    ]

    resultado = _fusionar(evaluaciones, peso_reglas=1.0, peso_ml=0.0)

    grupos = [d["grupo"] for d in resultado["detecciones"]]
    assert grupos == ["GF-05"]


def prueba_el_umbral_y_los_pesos_salen_de_ut03() -> None:
    motor = _motor()
    resultado = _fusionar([Evaluacion("GF-05", 1.0, 1715.0)])
    assert resultado["umbral"] == motor.umbral_confianza


def prueba_plan_b_con_peso_ml_en_cero_el_motor_funciona_sin_modelo(tmp_path) -> None:
    eje, intensidad = sim.espectro(sim.CETONA)

    resultado = identificar(
        eje,
        intensidad,
        obtener_catalogo().grupos,
        umbral=0.6,
        peso_reglas=1.0,
        peso_ml=0.0,
        via_ml=ViaML(tmp_path),
    )

    assert "GF-05" in [d["grupo"] for d in resultado["detecciones"]]


def prueba_si_ut03_pide_el_modelo_y_no_existe_el_motor_lo_dice(tmp_path) -> None:
    eje, intensidad = sim.espectro(sim.CETONA)
    with pytest.raises(ModeloNoDisponible):
        identificar(
            eje,
            intensidad,
            obtener_catalogo().grupos,
            umbral=0.6,
            peso_reglas=0.5,
            peso_ml=0.5,
            via_ml=ViaML(tmp_path),
        )


def prueba_cuando_las_vias_coinciden_sube_y_cuando_discrepan_baja() -> None:
    base = confianza(0.7, 0.7, 0.5, 0.5)
    assert confianza(0.7, 0.95, 0.5, 0.5) > base
    assert confianza(0.7, 0.1, 0.5, 0.5) < base


def prueba_el_resultado_sigue_el_contrato_de_la_seccion_5() -> None:
    eje, intensidad = sim.espectro(sim.CETONA)
    motor = _motor()

    resultado = identificar(
        eje,
        intensidad,
        obtener_catalogo().grupos,
        umbral=motor.umbral_confianza,
        peso_reglas=motor.peso_reglas,
        peso_ml=motor.peso_ml,
    )

    assert set(resultado) == {"detecciones", "sin_detecciones", "umbral"}
    carbonilo = next(d for d in resultado["detecciones"] if d["grupo"] == "GF-05")
    assert set(carbonilo) == {"grupo", "confianza", "region_cm1", "pico_cm1", "evidencia"}
    assert carbonilo["region_cm1"] == list(obtener_catalogo().grupo("GF-05").region_cm1)
    assert set(carbonilo["evidencia"]) == {"regla", "ml"}


def prueba_el_o_h_de_un_acido_trae_la_region_de_los_acidos() -> None:
    eje, intensidad = sim.espectro(sim.ACIDO_AROMATICO)
    resultado = identificar(
        eje, intensidad, obtener_catalogo().grupos,
        umbral=0.6, peso_reglas=1.0, peso_ml=0.0,
    )
    o_h = next(d for d in resultado["detecciones"] if d["grupo"] == "GF-01")
    assert o_h["region_cm1"] == [2500.0, 3300.0]
