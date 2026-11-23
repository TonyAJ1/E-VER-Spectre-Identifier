"""Pruebas de T-23: resaltar la región y marcar el pico en la gráfica.

CA-06.1 pide que, con un C=O detectado en 1715 cm⁻¹, al seleccionar ese grupo
la gráfica resalte la región de 1670 a 1780 cm⁻¹ y marque la posición del
pico. Se revisa lo que el visor tiene marcado y además el color de la gráfica
dentro y fuera de la región.
"""

from __future__ import annotations

import pytest

from backend.pruebas.apoyo_navegador import color_en, marcas, subir_en_la_pagina
from backend.utilerias.catalogo import obtener as obtener_catalogo
from motor_identificacion.pruebas import espectros_simulados as sim


def _csv(tmp_path, bandas, nombre="simulado.csv"):
    eje, intensidad = sim.espectro(bandas)
    ruta = tmp_path / nombre
    filas = ["numero de onda,absorbancia"] + [
        f"{x:.4f},{y:.6f}" for x, y in zip(eje, intensidad)
    ]
    ruta.write_text("\n".join(filas) + "\n", encoding="ascii")
    return ruta


def analizar_en_la_pagina(pagina, servidor, ruta) -> None:
    subir_en_la_pagina(pagina, servidor, ruta, ruta.name)
    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'detecciones'"
    )


def prueba_ca_06_1_al_seleccionar_c_o_se_resalta_su_region_y_su_pico(
    pagina, servidor: str, tmp_path, evidencia
) -> None:
    analizar_en_la_pagina(pagina, servidor, _csv(tmp_path, sim.CETONA))
    fuera_antes = color_en(pagina, 2500)

    pagina.locator('.deteccion[data-grupo="GF-05"] .boton-resaltar').click()

    (marca,) = marcas(pagina)
    assert marca["grupo"] == "GF-05"
    assert tuple(marca["region_cm1"]) == obtener_catalogo().grupo("GF-05").region_cm1
    assert marca["pico_cm1"] == pytest.approx(1715, abs=5)
    assert color_en(pagina, 1745) != color_en(pagina, 2500)
    assert color_en(pagina, 2500) == fuera_antes
    evidencia(pagina, "t23-ca-06-1-resaltado")


def prueba_volver_a_pulsar_quita_el_resaltado(pagina, servidor: str, tmp_path) -> None:
    analizar_en_la_pagina(pagina, servidor, _csv(tmp_path, sim.CETONA))
    boton = pagina.locator('.deteccion[data-grupo="GF-05"] .boton-resaltar')

    boton.click()
    boton.click()

    assert marcas(pagina) == []
    assert boton.get_attribute("aria-pressed") == "false"
