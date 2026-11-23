"""Pruebas de T-07 · Integración MOD-01 → api → MOD-02 → MOD-03.

Cierran el flujo de punta a punta con el contrato D-5 (sección 5 del plan):
`POST /api/validar`, campo `archivo`, 200 con veredicto y 500 solo ante fallo
interno. Hay dos niveles:

1. **API** (cliente de pruebas de FastAPI): cada CA de la sección 10 pasa por
   la misma puerta que usa la interfaz, con los módulos reales.
2. **Navegador** (Playwright contra un servidor uvicorn de verdad): CA-01.1 y
   CA-01.3 de punta a punta, con captura como evidencia. Con la variable
   `EVER_EVIDENCIA=<carpeta>` las capturas también se copian ahí.
"""

from __future__ import annotations

import dataclasses
import logging
import socket
import tempfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn
from fastapi.testclient import TestClient

from backend.api import aplicacion as modulo_api
from backend.api.aplicacion import RUTA_VALIDAR, crear_aplicacion
from backend.utilerias import mensajes
from backend.utilerias.configuracion import (
    Configuracion,
    ErrorDeConfiguracion,
)
from backend.utilerias.configuracion import obtener as obtener_configuracion

# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #

CAMPOS_RECHAZO = {"valido", "codigo", "titulo", "mensaje", "accion"}


@pytest.fixture(scope="module")
def cliente() -> Iterator[TestClient]:
    with TestClient(crear_aplicacion()) as cliente_http:
        yield cliente_http


def _enviar(cliente: TestClient, nombre: str, contenido: bytes):
    return cliente.post(
        RUTA_VALIDAR, files={"archivo": (nombre, contenido, "application/octet-stream")}
    )


def _fixture(carpeta: Path, nombre: str) -> bytes:
    return (carpeta / nombre).read_bytes()


def _assert_rechazo(respuesta, codigo: str) -> dict:
    assert respuesta.status_code == 200, "un rechazo es un resultado, no un error"
    cuerpo = respuesta.json()
    assert set(cuerpo) == CAMPOS_RECHAZO
    assert cuerpo["valido"] is False
    assert cuerpo["codigo"] == codigo
    esperado = mensajes.obtener(codigo)
    assert cuerpo["titulo"] == esperado.titulo
    assert cuerpo["mensaje"] == esperado.texto
    assert cuerpo["accion"] == esperado.accion
    return cuerpo


# --------------------------------------------------------------------------- #
# Nivel API · la sección 10 completa por la puerta de la interfaz
# --------------------------------------------------------------------------- #


def prueba_ca_01_1_el_jdx_valido_se_acepta_con_nombre_y_bytes(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    contenido = _fixture(carpeta_fixtures, "espectro-valido.jdx")

    respuesta = _enviar(cliente, "acetona.jdx", contenido)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    # Desde el incremento 2 la respuesta trae además el espectro procesado
    # (T-12); lo que pide CA-01.1 sigue igual.
    assert cuerpo["valido"] is True
    assert cuerpo["nombre"] == "acetona.jdx"
    assert cuerpo["bytes"] == len(contenido)


def prueba_ca_01_2_el_csv_del_tamano_maximo_exacto_se_acepta(
    cliente: TestClient, csv_tamano_maximo: Path
) -> None:
    contenido = csv_tamano_maximo.read_bytes()
    assert len(contenido) == obtener_configuracion().archivo.tamano_maximo_bytes

    respuesta = _enviar(cliente, "maximo.csv", contenido)

    assert respuesta.json()["valido"] is True
    assert respuesta.json()["bytes"] == len(contenido)


def prueba_ca_01_3_el_png_se_rechaza_con_el_mensaje_de_formato(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    respuesta = _enviar(cliente, "imagen.png", _fixture(carpeta_fixtures, "imagen.png"))

    cuerpo = _assert_rechazo(respuesta, mensajes.FORMATO_NO_SOPORTADO)
    for formato in obtener_configuracion().archivo.formatos_permitidos:
        assert formato in cuerpo["mensaje"]


def prueba_ca_02_1_el_csv_de_900_puntos_se_acepta(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    respuesta = _enviar(
        cliente,
        "espectro.csv",
        _fixture(carpeta_fixtures, "espectro-valido-900-puntos.csv"),
    )

    assert respuesta.json()["valido"] is True


def prueba_ca_02_2_un_byte_de_mas_se_rechaza_por_tamano(
    cliente: TestClient, csv_un_byte_de_mas: Path
) -> None:
    respuesta = _enviar(cliente, "grande.csv", csv_un_byte_de_mas.read_bytes())

    cuerpo = _assert_rechazo(respuesta, mensajes.TAMANO_EXCEDIDO)
    assert "tamaño máximo permitido" in cuerpo["mensaje"]


def prueba_ca_02_3_el_rango_corto_se_rechaza(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    respuesta = _enviar(
        cliente, "corto.csv", _fixture(carpeta_fixtures, "espectro-rango-corto.csv")
    )

    cuerpo = _assert_rechazo(respuesta, mensajes.RANGO_INSUFICIENTE)
    assert cuerpo["mensaje"].startswith("Se requiere cubrir al menos")


@pytest.mark.parametrize("archivo", ["archivo-vacio.csv", "espectro-truncado.jdx"])
def prueba_ca_02_4_vacio_o_truncado_da_motivo_y_se_atiende_la_siguiente(
    cliente: TestClient, carpeta_fixtures: Path, archivo: str
) -> None:
    roto = _enviar(cliente, archivo, _fixture(carpeta_fixtures, archivo))
    siguiente = _enviar(
        cliente, "bueno.jdx", _fixture(carpeta_fixtures, "espectro-valido.jdx")
    )

    _assert_rechazo(roto, mensajes.ESTRUCTURA_INVALIDA)
    assert siguiente.status_code == 200
    assert siguiente.json()["valido"] is True, "el servidor sigue atendiendo"


def prueba_ca_02_5_el_binario_disfrazado_se_rechaza_por_su_contenido(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    respuesta = _enviar(
        cliente, "programa.csv", _fixture(carpeta_fixtures, "binario-disfrazado.csv")
    )

    _assert_rechazo(respuesta, mensajes.ARCHIVO_NO_ES_TEXTO)


def prueba_ca_02_6_trescientos_entra_y_doscientos_noventa_y_nueve_no(
    cliente: TestClient, carpeta_fixtures: Path
) -> None:
    justo = _enviar(
        cliente, "300.csv", _fixture(carpeta_fixtures, "espectro-puntos-minimos.csv")
    )
    corto = _enviar(
        cliente, "299.csv", _fixture(carpeta_fixtures, "espectro-un-punto-menos.csv")
    )

    assert justo.json()["valido"] is True
    cuerpo = _assert_rechazo(corto, mensajes.PUNTOS_INSUFICIENTES)
    assert cuerpo["mensaje"] == (
        f"Mínimo {obtener_configuracion().validacion.puntos_minimos} puntos"
    )


# --------------------------------------------------------------------------- #
# Contrato D-5 · casos de borde
# --------------------------------------------------------------------------- #


def prueba_sin_campo_archivo_se_responde_con_motivo(cliente: TestClient) -> None:
    respuesta = cliente.post(RUTA_VALIDAR, data={"otro": "x"})

    _assert_rechazo(respuesta, mensajes.ARCHIVO_NO_RECIBIDO)


def prueba_un_fallo_interno_da_500_generico_sin_detalles(
    monkeypatch: pytest.MonkeyPatch, carpeta_fixtures: Path, caplog
) -> None:
    def estallar(*_: object, **__: object) -> None:
        raise RuntimeError("C:/temp/upload-9f2a.tmp 400.0 0.80 Traceback")

    monkeypatch.setattr(modulo_api, "validar", estallar)
    with TestClient(crear_aplicacion()) as cliente_http, caplog.at_level(logging.INFO):
        respuesta = _enviar(
            cliente_http, "a.jdx", _fixture(carpeta_fixtures, "espectro-valido.jdx")
        )

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert cuerpo["codigo"] == mensajes.ERROR_INTERNO
    assert cuerpo["mensaje"] == mensajes.obtener(mensajes.ERROR_INTERNO).texto
    visible = respuesta.text + "\n".join(r.getMessage() for r in caplog.records)
    for rastro in ("C:/temp", ".tmp", "Traceback", "400.0 0.80"):
        assert rastro not in visible


def prueba_la_api_usa_la_configuracion_de_ut03(carpeta_fixtures: Path) -> None:
    """Cambiar UT-03 cambia el veredicto de punta a punta, sin tocar código."""
    base = obtener_configuracion()
    exigente: Configuracion = dataclasses.replace(
        base,
        validacion=dataclasses.replace(
            base.validacion, puntos_minimos=base.validacion.puntos_minimos + 200
        ),
    )
    contenido = _fixture(carpeta_fixtures, "espectro-puntos-minimos.csv")

    with TestClient(crear_aplicacion(exigente)) as cliente_http:
        respuesta = _enviar(cliente_http, "e.csv", contenido)

    assert respuesta.json()["codigo"] == mensajes.PUNTOS_INSUFICIENTES
    assert str(base.validacion.puntos_minimos + 200) in respuesta.json()["mensaje"]


def prueba_con_ut03_incompleta_la_aplicacion_no_arranca(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def incompleta() -> Configuracion:
        raise ErrorDeConfiguracion("falta la llave obligatoria «validacion.puntos_minimos»")

    monkeypatch.setattr(modulo_api, "obtener_configuracion", incompleta)

    with pytest.raises(ErrorDeConfiguracion, match="puntos_minimos"):
        crear_aplicacion()


def prueba_la_raiz_lleva_a_la_interfaz(cliente: TestClient) -> None:
    respuesta = cliente.get("/", follow_redirects=True)

    assert respuesta.status_code == 200
    assert 'id="boton-analizar"' in respuesta.text


# --------------------------------------------------------------------------- #
# RNF-09 de punta a punta: nada del usuario se queda en disco ni en el registro
# --------------------------------------------------------------------------- #


def prueba_rnf_09_tras_la_peticion_no_queda_temporal_del_usuario(
    cliente: TestClient, csv_tres_megas: Path
) -> None:
    carpeta = Path(tempfile.gettempdir())
    antes = {p.name for p in carpeta.iterdir()}

    respuesta = _enviar(cliente, "tres-megas.csv", csv_tres_megas.read_bytes())

    despues = {p.name for p in carpeta.iterdir()}
    assert respuesta.json()["valido"] is True
    assert despues - antes == set(), f"quedó en el temporal: {despues - antes}"


def prueba_rnf_09_el_registro_guarda_nombre_y_resultado_no_el_contenido(
    cliente: TestClient, caplog
) -> None:
    contenido = b"400.0,0.512345\n500.0,0.698765\n"

    with caplog.at_level(logging.INFO):
        _enviar(cliente, "acetona.csv", contenido)

    registrado = "\n".join(r.getMessage() for r in caplog.records)
    assert "acetona.csv" in registrado
    assert "0.512345" not in registrado


# --------------------------------------------------------------------------- #
# Nivel navegador · servidor real + Chromium (CA-01.1 y CA-01.3 E2E)
# --------------------------------------------------------------------------- #


def _puerto_libre() -> int:
    with socket.socket() as zocalo:
        zocalo.bind(("127.0.0.1", 0))
        return zocalo.getsockname()[1]


@pytest.fixture(scope="module")
def servidor_real() -> Iterator[str]:
    """La aplicación real en uvicorn, en un hilo, en un puerto libre."""
    puerto = _puerto_libre()
    servidor = uvicorn.Server(
        uvicorn.Config(crear_aplicacion(), host="127.0.0.1", port=puerto, log_level="warning")
    )
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    limite = time.monotonic() + 15
    while not servidor.started:
        if time.monotonic() > limite:  # pragma: no cover - depende de la máquina
            pytest.fail("el servidor no arrancó en 15 s")
        time.sleep(0.05)
    yield f"http://127.0.0.1:{puerto}"
    servidor.should_exit = True
    hilo.join(timeout=10)


def _subir_en_el_navegador(pagina, base: str, ruta: Path, nombre: str) -> None:
    pagina.goto(base + "/")
    pagina.set_input_files(
        "#archivo",
        files=[{"name": nombre, "mimeType": "application/octet-stream",
                "buffer": ruta.read_bytes()}],
    )
    pagina.click("#boton-validar")
    pagina.wait_for_function(
        "['aceptado','rechazado','error'].includes("
        "document.getElementById('resultado').dataset.estado)"
    )


def prueba_e2e_ca_01_1_jdx_valido_acepta_muestra_nombre_y_habilita_analizar(
    pagina, servidor_real: str, carpeta_fixtures: Path, evidencia, caplog
) -> None:
    with caplog.at_level(logging.INFO):
        _subir_en_el_navegador(
            pagina, servidor_real, carpeta_fixtures / "espectro-valido.jdx",
            "acetona.jdx",
        )

    assert pagina.get_attribute("#resultado", "data-estado") == "aceptado"
    assert pagina.inner_text("#resultado-nombre") == "acetona.jdx"
    assert pagina.is_enabled("#boton-analizar")
    evidencia(pagina, "t07-ca-01-1-aceptado")
    registrado = "\n".join(r.getMessage() for r in caplog.records)
    assert "nombre=acetona.jdx" in registrado and "valido" in registrado


def prueba_e2e_ca_01_3_png_rechazado_con_mensaje_de_formato(
    pagina, servidor_real: str, carpeta_fixtures: Path, evidencia
) -> None:
    _subir_en_el_navegador(
        pagina, servidor_real, carpeta_fixtures / "imagen.png", "imagen.png"
    )

    esperado = mensajes.obtener(mensajes.FORMATO_NO_SOPORTADO)
    assert pagina.get_attribute("#resultado", "data-estado") == "rechazado"
    assert pagina.inner_text("#resultado-mensaje") == esperado.texto
    assert pagina.inner_text("#resultado-accion") == esperado.accion
    assert pagina.is_disabled("#boton-analizar")
    evidencia(pagina, "t07-ca-01-3-rechazado")


def prueba_e2e_ca_02_4_tras_un_vacio_el_siguiente_se_atiende(
    pagina, servidor_real: str, carpeta_fixtures: Path, evidencia
) -> None:
    _subir_en_el_navegador(
        pagina, servidor_real, carpeta_fixtures / "archivo-vacio.csv", "vacio.csv"
    )
    assert pagina.get_attribute("#resultado", "data-estado") == "rechazado"
    evidencia(pagina, "t07-ca-02-4-vacio")

    _subir_en_el_navegador(
        pagina, servidor_real, carpeta_fixtures / "espectro-valido-900-puntos.csv",
        "espectro.csv",
    )
    assert pagina.get_attribute("#resultado", "data-estado") == "aceptado"
