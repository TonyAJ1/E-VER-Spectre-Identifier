"""Pruebas de T-12: la gráfica del espectro con el eje invertido.

CA-04.1 pide que, con un espectro válido, al terminar la carga se vea la
gráfica con el número de onda en cm⁻¹ en el eje horizontal, de 4000 a 400, y
la intensidad en el eje vertical.

Hay tres niveles. La API entrega el espectro procesado junto al veredicto. El
visor de MOD-05 se prueba solo, contra un espectro simulado, como dice el
plan. Y al final el flujo completo en un navegador real, con captura como
evidencia.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.aplicacion import RUTA_VALIDAR, crear_aplicacion
from backend.pruebas.apoyo_navegador import subir_en_la_pagina as subir
from backend.utilerias.configuracion import obtener as obtener_configuracion

TITULO_EJE_X = "Número de onda (cm⁻¹)"


@pytest.fixture(scope="module")
def cliente() -> Iterator[TestClient]:
    with TestClient(crear_aplicacion()) as cliente_http:
        yield cliente_http


def opciones_de_la_grafica(pagina) -> dict | None:
    return pagina.evaluate(
        """() => {
            const g = window.EVER.visor.grafica(document.getElementById('grafica-lienzo'));
            if (!g) return null;
            const x = g.options.scales.x, y = g.options.scales.y;
            return {
                reverse: x.reverse, xmin: x.min, xmax: x.max,
                xtitulo: x.title.text, ytitulo: y.title.text,
                puntos: g.data.datasets[0].data.length,
                izquierda: g.scales.x.getValueForPixel(g.chartArea.left),
                derecha: g.scales.x.getValueForPixel(g.chartArea.right),
            };
        }"""
    )


# API


def prueba_la_api_entrega_el_espectro_procesado_al_aceptar(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    contenido = (carpeta_fixtures / "espectro-comprimido.jdx").read_bytes()

    cuerpo = cliente.post(
        RUTA_VALIDAR, files={"archivo": ("acetona.jdx", contenido, "text/plain")}
    ).json()

    procesamiento = obtener_configuracion().procesamiento
    espectro = cuerpo["espectro"]
    assert cuerpo["valido"] is True
    assert len(espectro["eje_cm1"]) == procesamiento.puntos_rejilla
    assert len(espectro["intensidad"]) == procesamiento.puntos_rejilla
    assert espectro["eje_cm1"][0] > espectro["eje_cm1"][-1]
    assert 0 <= min(espectro["intensidad"]) and max(espectro["intensidad"]) <= 1


# Visor solo, contra un espectro simulado


def prueba_el_visor_dibuja_un_espectro_simulado_con_el_eje_invertido(
    pagina, servidor: str
) -> None:
    pagina.goto(servidor + "/")
    pagina.evaluate(
        """() => {
            const eje = [], intensidad = [];
            for (let i = 0; i < 100; i++) {
                eje.push(4000 - i * 36);
                intensidad.push((i % 10) / 10);
            }
            document.getElementById('grafica').hidden = false;
            window.EVER.visor.dibujar(document.getElementById('grafica-lienzo'),
                { eje_cm1: eje, intensidad: intensidad, rango_medido_cm1: [436, 4000] });
        }"""
    )

    opciones = opciones_de_la_grafica(pagina)
    assert opciones["reverse"] is True
    assert opciones["izquierda"] == pytest.approx(4000)
    assert opciones["derecha"] == pytest.approx(436)
    assert opciones["puntos"] == 100


# Flujo completo en el navegador


def prueba_ca_04_1_al_cargar_se_ve_la_grafica_con_ejes_y_unidades(
    pagina, servidor: str, carpeta_fixtures: Path, evidencia
) -> None:
    subir(pagina, servidor, carpeta_fixtures / "espectro-valido.jdx", "espectro.jdx")

    assert pagina.get_attribute("#resultado", "data-estado") == "aceptado"
    assert pagina.is_visible("#grafica canvas")
    opciones = opciones_de_la_grafica(pagina)
    menor, mayor = obtener_configuracion().procesamiento.rango_rejilla_cm1
    assert opciones["reverse"] is True
    assert opciones["xtitulo"] == TITULO_EJE_X
    assert opciones["ytitulo"] == "Absorbancia normalizada"
    assert opciones["izquierda"] == pytest.approx(mayor)
    assert opciones["derecha"] == pytest.approx(menor)
    evidencia(pagina, "t12-ca-04-1-grafica")
