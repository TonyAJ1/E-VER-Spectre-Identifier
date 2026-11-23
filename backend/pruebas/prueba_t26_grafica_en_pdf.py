"""Pruebas de T-26: el reporte PDF incluye la gráfica con las regiones resaltadas.

La gráfica la dibuja la página con la misma librería de MOD-05 y la manda
como imagen PNG junto con los datos del análisis. El servidor revisa que de
verdad sea un PNG y la pone en el PDF.
"""

from __future__ import annotations

import base64
import os
import struct
import zlib
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend.api.aplicacion import crear_aplicacion
from backend.api.reporte import RUTA_REPORTE, PeticionInvalida, armar_datos
from backend.pruebas.prueba_t25_reporte import cuerpo_de_ejemplo, texto_del_pdf
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion


@pytest.fixture(scope="module")
def cliente():
    with TestClient(crear_aplicacion()) as cliente_http:
        yield cliente_http


def png_pequeno(ancho: int = 40, alto: int = 20) -> bytes:
    """Un PNG blanco hecho a mano, sin depender de ninguna librería."""

    def bloque(tipo: bytes, datos: bytes) -> bytes:
        return (
            struct.pack(">I", len(datos))
            + tipo
            + datos
            + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
        )

    cabecera = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    filas = b"".join(b"\x00" + b"\xff" * (ancho * 3) for _ in range(alto))
    return (
        b"\x89PNG\r\n\x1a\n"
        + bloque(b"IHDR", cabecera)
        + bloque(b"IDAT", zlib.compress(filas))
        + bloque(b"IEND", b"")
    )


def como_data_url(contenido: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(contenido).decode("ascii")


def imagenes_del_pdf(contenido: bytes) -> int:
    lector = PdfReader(BytesIO(contenido))
    return sum(len(pagina.images) for pagina in lector.pages)


def prueba_el_pdf_lleva_la_grafica_que_manda_la_pagina(cliente) -> None:
    cuerpo = cuerpo_de_ejemplo(imagen_png=como_data_url(png_pequeno()))
    respuesta = cliente.post(RUTA_REPORTE, json=cuerpo)

    assert respuesta.status_code == 200
    assert imagenes_del_pdf(respuesta.content) == 1
    assert "Espectro con las regiones resaltadas" in texto_del_pdf(respuesta.content)


def prueba_sin_grafica_el_pdf_lo_dice_en_lugar_de_dejar_un_hueco(cliente) -> None:
    respuesta = cliente.post(RUTA_REPORTE, json=cuerpo_de_ejemplo())

    assert respuesta.status_code == 200
    assert imagenes_del_pdf(respuesta.content) == 0
    assert "No se recibió la imagen de la gráfica" in texto_del_pdf(respuesta.content)


@pytest.mark.parametrize(
    "valor",
    [
        "data:image/jpeg;base64,AAAA",
        "data:image/png;base64,esto no es base64",
        como_data_url(b"GIF89a no es un png"),
        12345,
    ],
)
def prueba_una_imagen_que_no_es_png_se_rechaza(valor) -> None:
    with pytest.raises(PeticionInvalida):
        armar_datos(
            cuerpo_de_ejemplo(imagen_png=valor),
            obtener_configuracion(),
            obtener_catalogo(),
        )


def prueba_en_la_pagina_el_pdf_descargado_trae_la_grafica(
    pagina, servidor: str, tmp_path, evidencia
) -> None:
    from backend.pruebas.apoyo_navegador import subir_en_la_pagina
    from motor_identificacion.pruebas import espectros_simulados as sim

    eje, intensidad = sim.espectro(sim.CETONA)
    ruta = tmp_path / "cetona.csv"
    filas = ["numero de onda,absorbancia"] + [
        f"{x:.4f},{y:.6f}" for x, y in zip(eje, intensidad)
    ]
    ruta.write_text("\n".join(filas) + "\n", encoding="ascii")
    subir_en_la_pagina(pagina, servidor, ruta, "cetona.csv")
    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'detecciones'"
    )

    with pagina.expect_download() as descarga:
        pagina.click("#boton-reporte")
    archivo = tmp_path / "con_grafica.pdf"
    descarga.value.save_as(archivo)

    contenido = archivo.read_bytes()
    assert imagenes_del_pdf(contenido) == 1
    imagen = next(img for p in PdfReader(BytesIO(contenido)).pages for img in p.images)
    assert imagen.image.width >= 900
    evidencia(pagina, "t26-reporte-con-grafica")
    if os.environ.get("EVER_EVIDENCIA"):
        # La gráfica tal como quedó dentro del PDF, para la bitácora.
        destino = Path(os.environ["EVER_EVIDENCIA"]) / "t26-grafica-dentro-del-pdf.png"
        destino.write_bytes(imagen.data)
