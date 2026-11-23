"""Pruebas de T-24: grupos que se enciman y grupo sin posición de pico.

CA-06.2 pide que, con O–H y N–H detectados en regiones que se enciman, cada
grupo se distinga con su propio color y una leyenda. CA-06.3 pide que, si el
motor no reporta la posición exacta del pico, se resalte la región completa en
lugar de dejar la gráfica sin marca.

Las detecciones se simulan en la respuesta de /api/analizar, porque lo que se
prueba aquí es la gráfica y no el motor.
"""

from __future__ import annotations

import json

from backend.pruebas.apoyo_navegador import color_en, marcas, subir_en_la_pagina
from backend.utilerias.catalogo import obtener as obtener_catalogo


def _deteccion(grupo: str, pico, confianza: float) -> dict:
    datos = obtener_catalogo().grupo(grupo)
    return {
        "grupo": grupo,
        "nombre": datos.nombre,
        "familias": datos.familias,
        "confianza": confianza,
        "porcentaje": round(confianza * 100),
        "region_cm1": list(datos.region_cm1),
        "pico_cm1": pico,
        "evidencia": {"regla": confianza, "ml": None},
    }


def _con_detecciones(pagina, servidor, carpeta_fixtures, detecciones) -> None:
    cuerpo = {"detecciones": detecciones, "sin_detecciones": False, "umbral": 0.6}
    pagina.route(
        "**/api/analizar",
        lambda ruta: ruta.fulfill(
            status=200, content_type="application/json", body=json.dumps(cuerpo)
        ),
    )
    subir_en_la_pagina(
        pagina, servidor, carpeta_fixtures / "espectro-valido.jdx", "espectro.jdx"
    )
    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'detecciones'"
    )


def prueba_ca_06_2_o_h_y_n_h_se_distinguen_con_color_y_leyenda(
    pagina, servidor: str, carpeta_fixtures, evidencia
) -> None:
    _con_detecciones(
        pagina, servidor, carpeta_fixtures,
        [_deteccion("GF-01", 3350.0, 0.8), _deteccion("GF-02", 3420.0, 0.7)],
    )

    pagina.locator('.deteccion[data-grupo="GF-01"] .boton-resaltar').click()
    pagina.locator('.deteccion[data-grupo="GF-02"] .boton-resaltar').click()

    colores = {marca["grupo"]: marca["color"] for marca in marcas(pagina)}
    assert set(colores) == {"GF-01", "GF-02"}
    assert colores["GF-01"] != colores["GF-02"]
    leyenda = pagina.locator("#grafica-leyenda .leyenda-elemento")
    assert leyenda.count() == 2
    textos = leyenda.all_inner_texts()
    assert any("O–H" in t for t in textos) and any("N–H" in t for t in textos)
    assert color_en(pagina, 3250) != color_en(pagina, 3400)
    evidencia(pagina, "t24-ca-06-2-traslape")


def prueba_ca_06_3_sin_posicion_de_pico_se_resalta_la_region_completa(
    pagina, servidor: str, carpeta_fixtures, evidencia
) -> None:
    _con_detecciones(pagina, servidor, carpeta_fixtures, [_deteccion("GF-05", None, 0.7)])
    fuera = color_en(pagina, 2500)

    pagina.locator('.deteccion[data-grupo="GF-05"] .boton-resaltar').click()

    (marca,) = marcas(pagina)
    assert marca["pico_cm1"] is None
    menor, mayor = obtener_catalogo().grupo("GF-05").region_cm1
    for onda in (menor + 5, (menor + mayor) / 2, mayor - 5):
        assert color_en(pagina, onda) != fuera
    assert "región completa" in pagina.inner_text("#grafica-leyenda")
    evidencia(pagina, "t24-ca-06-3-sin-pico")
