"""Pruebas de T-25: el reporte PDF con los datos del análisis.

CA-09.1 pide un PDF con el nombre del archivo, la fecha y hora, cada grupo con
su confianza y su explicación y el aviso de resultado orientativo. La gráfica
resaltada es de T-26. Además, el PDF se arma en memoria y no se guarda en el
servidor (RNF-09).
"""

from __future__ import annotations

import builtins
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

from backend.api.aplicacion import crear_aplicacion
from backend.api.reporte import RUTA_REPORTE
from backend.utilerias import mensajes
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.catalogo import obtener_plantillas


@pytest.fixture(scope="module")
def cliente():
    with TestClient(crear_aplicacion()) as cliente_http:
        yield cliente_http


def cuerpo_de_ejemplo(**cambios) -> dict:
    cuerpo = {
        "nombre_archivo": "acetona.jdx",
        "fecha_hora": "2026-11-23T15:41:00-06:00",
        "detecciones": [
            {"grupo": "GF-03", "confianza": 0.73, "region_cm1": [2850, 2960], "pico_cm1": 2965.0},
            {"grupo": "GF-05", "confianza": 1.0, "region_cm1": [1670, 1780], "pico_cm1": 1715.0},
        ],
    }
    cuerpo.update(cambios)
    return cuerpo


def texto_del_pdf(contenido: bytes) -> str:
    lector = PdfReader(BytesIO(contenido))
    texto = "\n".join(pagina.extract_text() for pagina in lector.pages)
    return " ".join(texto.split())


def prueba_ca_09_1_el_pdf_trae_archivo_fecha_grupos_explicaciones_y_aviso(cliente) -> None:
    respuesta = cliente.post(RUTA_REPORTE, json=cuerpo_de_ejemplo())

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert "attachment" in respuesta.headers["content-disposition"]
    assert respuesta.content.startswith(b"%PDF")

    texto = texto_del_pdf(respuesta.content)
    assert "acetona.jdx" in texto
    assert "23/11/2026 15:41" in texto
    assert "C=O: 100 % de confianza" in texto
    assert "73 % de confianza" in texto
    assert "de 1670 a 1780 cm⁻¹" in texto
    assert "1715 cm⁻¹" in texto
    por_que = " ".join(obtener_plantillas()["GF-05"].por_que.split())
    assert por_que[:60] in texto
    aviso = " ".join(mensajes.obtener(mensajes.RESULTADO_ORIENTATIVO).texto.split())
    assert aviso[:60] in texto


def prueba_los_grupos_van_de_mayor_a_menor_confianza(cliente) -> None:
    texto = texto_del_pdf(cliente.post(RUTA_REPORTE, json=cuerpo_de_ejemplo()).content)
    assert texto.index("C=O:") < texto.index(obtener_catalogo().grupo("GF-03").nombre + ":")


def prueba_los_textos_salen_del_catalogo_y_no_de_la_pagina(cliente) -> None:
    cuerpo = cuerpo_de_ejemplo()
    cuerpo["detecciones"][0]["nombre"] = "texto inventado"
    texto = texto_del_pdf(cliente.post(RUTA_REPORTE, json=cuerpo).content)
    assert "texto inventado" not in texto


def prueba_rnf_09_el_pdf_se_arma_sin_escribir_en_disco(
    cliente, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.reportes.generador import _registrar_fuentes

    _registrar_fuentes()  # las fuentes se leen una vez; leer no es escribir
    escritos: list[str] = []
    original = builtins.open

    def vigilado(archivo, modo="r", *args, **kwargs):
        if any(letra in modo for letra in "wax+"):
            escritos.append(str(archivo))
        return original(archivo, modo, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", vigilado)
    respuesta = cliente.post(RUTA_REPORTE, json=cuerpo_de_ejemplo())

    assert respuesta.status_code == 200
    assert escritos == []


def prueba_en_la_pagina_descargar_reporte_baja_el_pdf(
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
    archivo = tmp_path / "descargado.pdf"
    descarga.value.save_as(archivo)

    assert descarga.value.suggested_filename == "reporte_analisis.pdf"
    texto = texto_del_pdf(archivo.read_bytes())
    assert "cetona.csv" in texto and "C=O" in texto
    evidencia(pagina, "t25-boton-reporte")
