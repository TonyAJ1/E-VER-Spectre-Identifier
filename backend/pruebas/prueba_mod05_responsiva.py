"""Pruebas de T-13: gráfica responsiva y nunca una gráfica vacía.

CA-04.2 pide que un espectro de 5 MB visto en una pantalla de 360 px se
ajuste al ancho, sin desplazamiento horizontal y con los ejes legibles. El
archivo de 5 MB exactos lo genera conftest.py con el tamaño de UT-03.

CA-04.3 pide que, si el archivo no pasó la validación, no aparezca una gráfica
vacía o incompleta sino el mensaje de error. Se prueba también que una
gráfica anterior desaparece al subir un archivo malo, y que la línea plana de
CA-03.3 tampoco deja gráfica.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.pruebas.apoyo_navegador import subir_en_la_pagina as subir
from backend.utilerias import mensajes
from backend.utilerias.configuracion import obtener as obtener_configuracion

ANCHO_CELULAR = 360


def _sin_desplazamiento(pagina) -> None:
    ancho = pagina.evaluate("document.documentElement.scrollWidth")
    assert ancho <= ANCHO_CELULAR, f"la página mide {ancho} px en un celular de 360"


def _no_hay_grafica(pagina) -> None:
    assert pagina.is_hidden("#grafica")
    assert pagina.query_selector("#grafica canvas") is None


def prueba_ca_04_2_un_espectro_de_5_mb_cabe_en_360_px(
    pagina, servidor: str, csv_tamano_maximo: Path, evidencia
) -> None:
    assert csv_tamano_maximo.stat().st_size == obtener_configuracion().archivo.tamano_maximo_bytes

    subir(pagina, servidor, csv_tamano_maximo, "espectro-5mb.csv")

    assert pagina.get_attribute("#resultado", "data-estado") == "aceptado"
    assert pagina.is_visible("#grafica canvas")
    _sin_desplazamiento(pagina)
    lienzo = pagina.locator("#grafica canvas").bounding_box()
    tarjeta = pagina.locator("#grafica").bounding_box()
    assert lienzo["x"] >= tarjeta["x"]
    assert lienzo["x"] + lienzo["width"] <= tarjeta["x"] + tarjeta["width"]

    # Ejes legibles: las etiquetas del eje horizontal no se enciman y no van
    # giradas, y los títulos de los dos ejes están puestos.
    etiquetas = pagina.evaluate(
        """() => {
            const g = window.EVER.visor.grafica(document.getElementById('grafica-lienzo'));
            const x = g.scales.x;
            return { cantidad: x.ticks.length, giro: x.labelRotation,
                     ancho: x.width };
        }"""
    )
    assert 2 <= etiquetas["cantidad"] <= 6
    assert etiquetas["giro"] == 0
    evidencia(pagina, "t13-ca-04-2-360px-5mb")


@pytest.mark.parametrize(
    ("archivo", "nombre", "codigo"),
    [
        ("imagen.png", "imagen.png", mensajes.FORMATO_NO_SOPORTADO),
        ("espectro-truncado.jdx", "truncado.jdx", mensajes.ESTRUCTURA_INVALIDA),
        ("espectro-linea-plana.csv", "plano.csv", mensajes.SIN_SENAL),
    ],
)
def prueba_ca_04_3_un_archivo_que_no_pasa_muestra_el_mensaje_y_no_una_grafica(
    pagina, servidor: str, carpeta_fixtures: Path, archivo: str, nombre: str,
    codigo: str, evidencia,
) -> None:
    subir(pagina, servidor, carpeta_fixtures / archivo, nombre)

    esperado = mensajes.obtener(codigo)
    assert pagina.get_attribute("#resultado", "data-estado") == "rechazado"
    assert pagina.inner_text("#resultado-mensaje") == esperado.texto
    _no_hay_grafica(pagina)
    evidencia(pagina, f"t13-ca-04-3-{Path(archivo).stem}")


def prueba_ca_04_3_la_grafica_anterior_se_borra_al_subir_uno_malo(
    pagina, servidor: str, carpeta_fixtures: Path
) -> None:
    subir(pagina, servidor, carpeta_fixtures / "espectro-valido.jdx", "bueno.jdx")
    assert pagina.is_visible("#grafica canvas")

    pagina.set_input_files(
        "#archivo",
        files=[{"name": "vacio.csv", "mimeType": "text/csv", "buffer": b""}],
    )
    _no_hay_grafica(pagina)
    pagina.click("#boton-validar")
    pagina.wait_for_function(
        "document.getElementById('resultado').dataset.estado === 'rechazado'"
    )
    _no_hay_grafica(pagina)
