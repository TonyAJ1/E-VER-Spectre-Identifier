"""Pruebas de T-27: el reporte sin detecciones y el fallo al generar el PDF.

CA-09.2 pide que, cuando el análisis no encontró nada confiable, el PDF se
genere de todos modos y lo diga con claridad. CA-09.3 pide que, si el PDF no
se puede generar, el usuario vea un mensaje, pueda volver a intentarlo y no
pierda los resultados de la pantalla.

Al final va la prueba de punta a punta de toda la aplicación, que el plan
pide para cerrar el incremento 5.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.api import reporte as ruta_reporte
from backend.api.aplicacion import crear_aplicacion
from backend.api.reporte import RUTA_REPORTE
from backend.pruebas.prueba_t25_reporte import cuerpo_de_ejemplo, texto_del_pdf
from backend.utilerias import mensajes
from motor_identificacion.pruebas import espectros_simulados as sim


@pytest.fixture(scope="module")
def cliente():
    with TestClient(crear_aplicacion()) as cliente_http:
        yield cliente_http


def escribir_csv(ruta, bandas, **opciones) -> None:
    eje, intensidad = sim.espectro(bandas, **opciones)
    filas = ["numero de onda,absorbancia"] + [
        f"{x:.4f},{y:.6f}" for x, y in zip(eje, intensidad)
    ]
    ruta.write_text("\n".join(filas) + "\n", encoding="ascii")


# CA-09.2


def prueba_ca_09_2_sin_detecciones_el_pdf_dice_que_no_hubo_confiables(cliente) -> None:
    respuesta = cliente.post(RUTA_REPORTE, json=cuerpo_de_ejemplo(detecciones=[]))

    assert respuesta.status_code == 200
    texto = texto_del_pdf(respuesta.content)
    assert "No se encontraron detecciones confiables" in texto
    assert "60 %" in texto
    assert "de confianza" in texto
    aviso = " ".join(mensajes.obtener(mensajes.RESULTADO_ORIENTATIVO).texto.split())
    assert aviso[:60] in texto


def prueba_con_detecciones_el_pdf_no_trae_la_leyenda(cliente) -> None:
    texto = texto_del_pdf(cliente.post(RUTA_REPORTE, json=cuerpo_de_ejemplo()).content)
    assert "No se encontraron detecciones confiables" not in texto


def prueba_ca_09_2_en_la_pagina_se_baja_el_reporte_sin_detecciones(
    pagina, servidor: str, tmp_path, evidencia
) -> None:
    from backend.pruebas.apoyo_navegador import subir_en_la_pagina

    ruta = tmp_path / "ruidoso.csv"
    escribir_csv(ruta, [(2000, 0.0, 10)], ruido=0.05)
    subir_en_la_pagina(pagina, servidor, ruta, "ruidoso.csv")
    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'sin-detecciones'"
    )

    assert pagina.is_visible("#boton-reporte")
    with pagina.expect_download() as descarga:
        pagina.click("#boton-reporte")
    archivo = tmp_path / "sin_detecciones.pdf"
    descarga.value.save_as(archivo)

    texto = texto_del_pdf(archivo.read_bytes())
    assert "ruidoso.csv" in texto
    assert "No se encontraron detecciones confiables" in texto
    evidencia(pagina, "t27-ca-09-2-reporte-sin-detecciones")


# CA-09.3


def prueba_ca_09_3_si_mod_08_falla_llega_el_mensaje_de_ut_02_sin_detalles(
    cliente, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fallar(*args, **kwargs):
        raise RuntimeError("detalle interno que el usuario no debe ver")

    monkeypatch.setattr(ruta_reporte, "generar_pdf", fallar)
    respuesta = cliente.post(RUTA_REPORTE, json=cuerpo_de_ejemplo())

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    esperado = mensajes.obtener(mensajes.REPORTE_FALLIDO)
    assert cuerpo == {
        "codigo": esperado.codigo,
        "titulo": esperado.titulo,
        "mensaje": esperado.texto,
        "accion": esperado.accion,
    }
    assert "detalle interno" not in respuesta.text
    assert "RuntimeError" not in respuesta.text


@pytest.mark.parametrize(
    "contenido",
    [
        b"esto no es json",
        json.dumps([1, 2, 3]).encode(),
        json.dumps(cuerpo_de_ejemplo(fecha_hora="ayer")).encode(),
        json.dumps(cuerpo_de_ejemplo(imagen_png="data:image/gif;base64,AAAA")).encode(),
    ],
)
def prueba_un_cuerpo_que_no_sirve_da_400_con_el_mismo_mensaje(cliente, contenido) -> None:
    respuesta = cliente.post(
        RUTA_REPORTE, content=contenido, headers={"Content-Type": "application/json"}
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == mensajes.REPORTE_FALLIDO


def prueba_ca_09_3_en_la_pagina_hay_mensaje_reintento_y_resultados_conservados(
    pagina, servidor: str, tmp_path, evidencia
) -> None:
    from backend.pruebas.apoyo_navegador import subir_en_la_pagina

    ruta = tmp_path / "cetona.csv"
    escribir_csv(ruta, sim.CETONA)
    subir_en_la_pagina(pagina, servidor, ruta, "cetona.csv")
    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'detecciones'"
    )
    grupos_antes = pagina.locator(".deteccion").count()
    assert grupos_antes > 0

    # Fallo simulado: la primera vez el servidor contesta 500 con el mensaje
    # de UT-02; la segunda vez la petición llega al servidor de verdad.
    fallo = mensajes.obtener(mensajes.REPORTE_FALLIDO)
    intentos = {"cuenta": 0}

    def interceptar(ruta_red):
        intentos["cuenta"] += 1
        if intentos["cuenta"] == 1:
            ruta_red.fulfill(
                status=500,
                content_type="application/json",
                body=json.dumps(
                    {"codigo": fallo.codigo, "titulo": fallo.titulo,
                     "mensaje": fallo.texto, "accion": fallo.accion}
                ),
            )
        else:
            ruta_red.continue_()

    pagina.route("**" + RUTA_REPORTE, interceptar)
    pagina.click("#boton-reporte")
    pagina.wait_for_selector("#reporte-estado:not([hidden])")

    assert pagina.inner_text("#reporte-mensaje") == fallo.texto
    assert pagina.inner_text("#reporte-accion") == fallo.accion
    assert pagina.locator(".deteccion").count() == grupos_antes
    assert pagina.is_visible("#grafica-lienzo")
    pagina.wait_for_function("!document.getElementById('boton-reporte').disabled")
    evidencia(pagina, "t27-ca-09-3-fallo-del-reporte")

    with pagina.expect_download() as descarga:
        pagina.click("#boton-reporte")
    assert descarga.value.suggested_filename == "reporte_analisis.pdf"
    assert intentos["cuenta"] == 2
    assert pagina.is_hidden("#reporte-estado")


# Punta a punta


def prueba_de_punta_a_punta_subir_ver_analizar_resaltar_y_descargar(
    pagina, servidor: str, tmp_path, evidencia
) -> None:
    from backend.pruebas.apoyo_navegador import marcas, subir_en_la_pagina

    ruta = tmp_path / "cetona.csv"
    escribir_csv(ruta, sim.CETONA)

    # Incremento 1: el archivo se sube y se acepta.
    subir_en_la_pagina(pagina, servidor, ruta, "cetona.csv")
    assert pagina.get_attribute("#resultado", "data-estado") == "aceptado"

    # Incremento 2: la gráfica aparece.
    assert pagina.is_visible("#grafica-lienzo")

    # Incremento 3: el análisis encuentra el carbonilo.
    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'detecciones'"
    )
    assert pagina.locator(".deteccion[data-grupo='GF-05']").count() == 1

    # Incremento 4: la explicación existe y el grupo se resalta.
    tarjeta = pagina.locator(".deteccion[data-grupo='GF-05']")
    assert tarjeta.locator("details").count() == 1
    tarjeta.locator(".boton-resaltar").click()
    assert [m["grupo"] for m in marcas(pagina)] == ["GF-05"]

    # Incremento 5: el reporte se descarga con todo.
    with pagina.expect_download() as descarga:
        pagina.click("#boton-reporte")
    archivo = tmp_path / "completo.pdf"
    descarga.value.save_as(archivo)
    texto = texto_del_pdf(archivo.read_bytes())
    assert "cetona.csv" in texto
    assert "C=O" in texto
    assert "Espectro con las regiones resaltadas" in texto
    evidencia(pagina, "t27-punta-a-punta")
