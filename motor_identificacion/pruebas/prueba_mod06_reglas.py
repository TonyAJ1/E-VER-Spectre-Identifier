"""Pruebas de T-15: la vía de reglas de MOD-06.

La prueba del plan es que un espectro de acetona dé C=O detectado con su
región. El espectro real de NIST no se puede guardar en el repositorio, así
que aquí se usa una cetona simulada con su banda en 1715 cm⁻¹; la prueba con
el archivo real está con CA-05.1 en el incremento 3 y se salta si el archivo
no está descargado.

También se revisa que cada grupo responda a su banda, que O–H y N–H se
distingan por el ancho, que el alqueno y el aromático necesiten su C–H por
encima de 3000 cm⁻¹ y que el ruido no se confunda con señal.
"""

from __future__ import annotations

import pytest

from backend.utilerias.catalogo import obtener as obtener_catalogo
from motor_identificacion.pruebas import espectros_simulados as sim
from motor_identificacion.reglas.picos import encontrar
from motor_identificacion.reglas.via_reglas import evaluar


def _puntajes(bandas, **opciones) -> dict:
    eje, intensidad = sim.espectro(bandas, **opciones)
    return {e.grupo: e for e in evaluar(eje, intensidad, obtener_catalogo().grupos)}


def prueba_la_cetona_da_c_o_claro_en_su_region() -> None:
    resultado = _puntajes(sim.CETONA)["GF-05"]

    assert resultado.puntaje >= 0.9
    menor, mayor = obtener_catalogo().grupo("GF-05").region_cm1
    assert menor <= resultado.pico_cm1 <= mayor
    assert resultado.pico_cm1 == pytest.approx(1715, abs=5)


@pytest.mark.parametrize(
    ("bandas", "esperado"),
    [
        (sim.ALCOHOL, "GF-01"),
        (sim.AMINA, "GF-02"),
        (sim.CETONA, "GF-03"),
        (sim.NITRILO, "GF-04"),
        (sim.ALQUENO, "GF-06"),
        (sim.AROMATICO, "GF-07"),
    ],
)
def prueba_cada_grupo_responde_a_su_banda(bandas, esperado: str) -> None:
    assert _puntajes(bandas)[esperado].puntaje >= 0.6


def prueba_la_banda_ancha_es_o_h_y_no_n_h() -> None:
    puntajes = _puntajes(sim.ALCOHOL)
    assert puntajes["GF-01"].puntaje >= 0.6
    assert puntajes["GF-02"].puntaje < 0.4


def prueba_las_bandas_angostas_son_n_h_y_no_o_h() -> None:
    puntajes = _puntajes(sim.AMINA)
    assert puntajes["GF-02"].puntaje >= 0.6
    assert puntajes["GF-01"].puntaje < 0.4


def prueba_sin_su_c_h_el_aromatico_no_pasa() -> None:
    sin_c_h = [banda for banda in sim.AROMATICO if banda[0] < 3000]
    assert _puntajes(sin_c_h)["GF-07"].puntaje < 0.6


def prueba_un_espectro_sin_banda_en_la_region_da_cero() -> None:
    assert _puntajes(sim.CETONA)["GF-04"].puntaje == 0
    assert _puntajes(sim.CETONA)["GF-04"].pico_cm1 is None


def prueba_el_ruido_puro_no_da_ningun_grupo_claro() -> None:
    puntajes = _puntajes([(2000, 0.0, 10)], ruido=0.05)
    assert max(p.puntaje for p in puntajes.values()) < 0.6


def prueba_los_puntajes_quedan_entre_0_y_1() -> None:
    for bandas in (sim.CETONA, sim.ACIDO_AROMATICO, sim.ALCOHOL):
        for resultado in _puntajes(bandas).values():
            assert 0 <= resultado.puntaje <= 1


def prueba_el_detector_mide_altura_prominencia_y_ancho() -> None:
    eje = [float(x) for x in range(100)]
    valores = [max(0.0, 1 - abs(x - 50) / 10) for x in eje]

    (pico,) = encontrar(eje, valores)

    assert pico.posicion_cm1 == 50
    assert pico.prominencia == pytest.approx(1)
    assert pico.ancho_cm1 == pytest.approx(10)
