"""Pruebas de T-06 · MOD-01 · Interfaz mínima, con veredictos **simulados**.

La sección 9 del plan pide probar MOD-01 aislado: «con un veredicto simulado →
la vista correcta». Aquí no hay backend: la página se sirve con un servidor de
archivos estáticos y la llamada a `/api/validar` la contesta la propia prueba
(Playwright intercepta la petición). Así se prueba **solo** la interfaz.

Lo que se verifica:

- Aceptado → aviso de documento aprobado, el **nombre** del archivo y
  «Analizar» **habilitado y sin acción** (D-4; CA-01.1 se cierra en T-07).
- Rechazado → título, motivo y acción **tal como los manda UT-02** (RNF-01).
- 500 y sin conexión → un mensaje claro, sin detalles técnicos.
- El nombre del archivo se muestra como texto, nunca como HTML.
- A 360 px no hay desplazamiento horizontal (adelanto de RNF-05).
- La interfaz no repite valores de UT-03.

Las pestañas abren a 360 px de ancho (fixture `pagina` de conftest).
"""

from __future__ import annotations

import functools
import json
import re
import threading
from collections.abc import Iterator
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from backend.utilerias import mensajes
from backend.utilerias.configuracion import obtener as obtener_configuracion

RAIZ = Path(__file__).resolve().parents[2]
CARPETA_FRONTEND = RAIZ / "frontend"
RUTA_PAGINA = "/interfaz/index.html"

# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #


class _Silencioso(SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:  # noqa: D401 - sin ruido
        pass


@pytest.fixture(scope="module")
def servidor_estatico() -> Iterator[str]:
    """Sirve `frontend/` en un puerto libre; devuelve la URL base."""
    manejador = functools.partial(_Silencioso, directory=str(CARPETA_FRONTEND))
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), manejador)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    yield f"http://127.0.0.1:{servidor.server_address[1]}"
    servidor.shutdown()
    servidor.server_close()


def _simular(pagina, estado: int, cuerpo: dict | None, peticiones: list) -> None:
    """Contesta `/api/validar` con lo que diga la prueba y anota cada llamada."""

    def responder(ruta) -> None:
        peticiones.append(ruta.request)
        ruta.fulfill(
            status=estado,
            content_type="application/json",
            body=json.dumps(cuerpo) if cuerpo is not None else "no es json",
        )

    pagina.route("**/api/validar", responder)


def _abrir_y_subir(pagina, base: str, nombre: str = "acetona.jdx") -> None:
    pagina.goto(base + RUTA_PAGINA)
    pagina.set_input_files(
        "#archivo",
        files=[{"name": nombre, "mimeType": "text/plain", "buffer": b"##TITLE=x\n"}],
    )
    pagina.click("#boton-validar")
    pagina.wait_for_function(
        "document.getElementById('resultado').dataset.estado !== 'validando'"
    )


def _rechazo_de_ut02(codigo: str) -> dict:
    """El cuerpo que mandaría la API para un rechazo (contrato D-5)."""
    mensaje = mensajes.obtener(codigo)
    return {
        "valido": False,
        "codigo": mensaje.codigo,
        "titulo": mensaje.titulo,
        "mensaje": mensaje.texto,
        "accion": mensaje.accion,
    }


# --------------------------------------------------------------------------- #
# Estado inicial
# --------------------------------------------------------------------------- #


def prueba_al_abrir_analizar_esta_presente_y_deshabilitado(
    pagina, servidor_estatico: str
) -> None:
    pagina.goto(servidor_estatico + RUTA_PAGINA)

    assert pagina.is_visible("#boton-analizar")
    assert pagina.is_disabled("#boton-analizar")
    assert pagina.is_disabled("#boton-validar"), "sin archivo no hay qué validar"
    assert pagina.is_hidden("#resultado")


def prueba_la_peticion_sigue_el_contrato_d5(pagina, servidor_estatico: str) -> None:
    peticiones: list = []
    _simular(
        pagina, 200, {"valido": True, "nombre": "acetona.jdx", "bytes": 10}, peticiones
    )

    _abrir_y_subir(pagina, servidor_estatico)

    assert len(peticiones) == 1
    peticion = peticiones[0]
    assert peticion.method == "POST"
    assert peticion.url.endswith("/api/validar")
    assert "multipart/form-data" in peticion.headers["content-type"]
    assert 'name="archivo"' in peticion.post_data_buffer.decode("latin-1")


# --------------------------------------------------------------------------- #
# Veredicto simulado · aceptado
# --------------------------------------------------------------------------- #


def prueba_aceptado_muestra_nombre_y_habilita_analizar(
    pagina, servidor_estatico: str, evidencia
) -> None:
    _simular(
        pagina, 200, {"valido": True, "nombre": "acetona.jdx", "bytes": 307200}, []
    )

    _abrir_y_subir(pagina, servidor_estatico)

    assert pagina.get_attribute("#resultado", "data-estado") == "aceptado"
    assert pagina.inner_text("#resultado-titulo") == "Documento aprobado"
    assert pagina.inner_text("#resultado-nombre") == "acetona.jdx"
    assert pagina.is_enabled("#boton-analizar")
    evidencia(pagina, "t06-aceptado-simulado")


def prueba_analizar_no_tiene_accion_en_este_incremento(
    pagina, servidor_estatico: str
) -> None:
    """D-4: presente y habilitado. Desde el incremento 3, si la respuesta no
    trae espectro procesado, «Analizar» no tiene nada que mandar al motor."""
    peticiones: list = []
    _simular(
        pagina, 200, {"valido": True, "nombre": "acetona.jdx", "bytes": 10}, peticiones
    )
    _abrir_y_subir(pagina, servidor_estatico)
    url_antes = pagina.url
    antes = pagina.inner_text("main")

    pagina.click("#boton-analizar")

    assert pagina.url == url_antes
    assert pagina.inner_text("main") == antes
    assert len(peticiones) == 1, "«Analizar» no debe llamar al servidor"


def prueba_elegir_otro_archivo_borra_el_veredicto_anterior(
    pagina, servidor_estatico: str
) -> None:
    _simular(
        pagina, 200, {"valido": True, "nombre": "acetona.jdx", "bytes": 10}, []
    )
    _abrir_y_subir(pagina, servidor_estatico)

    pagina.set_input_files(
        "#archivo",
        files=[{"name": "otro.csv", "mimeType": "text/csv", "buffer": b"1,2\n"}],
    )

    assert pagina.is_hidden("#resultado")
    assert pagina.is_disabled("#boton-analizar")


# --------------------------------------------------------------------------- #
# Veredicto simulado · rechazado
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "codigo",
    [
        mensajes.FORMATO_NO_SOPORTADO,
        mensajes.TAMANO_EXCEDIDO,
        mensajes.RANGO_INSUFICIENTE,
        mensajes.PUNTOS_INSUFICIENTES,
        mensajes.ARCHIVO_NO_ES_TEXTO,
        mensajes.ESTRUCTURA_INVALIDA,
    ],
)
def prueba_rechazado_muestra_motivo_y_accion_de_ut02(
    pagina, servidor_estatico: str, codigo: str
) -> None:
    cuerpo = _rechazo_de_ut02(codigo)
    _simular(pagina, 200, cuerpo, [])

    _abrir_y_subir(pagina, servidor_estatico, "espectro.csv")

    assert pagina.get_attribute("#resultado", "data-estado") == "rechazado"
    assert pagina.inner_text("#resultado-titulo") == cuerpo["titulo"]
    assert pagina.inner_text("#resultado-mensaje") == cuerpo["mensaje"]
    assert pagina.inner_text("#resultado-accion") == cuerpo["accion"]
    assert pagina.is_disabled("#boton-analizar")


def prueba_rechazado_evidencia_a_360_px(
    pagina, servidor_estatico: str, evidencia
) -> None:
    _simular(pagina, 200, _rechazo_de_ut02(mensajes.PUNTOS_INSUFICIENTES), [])

    _abrir_y_subir(pagina, servidor_estatico, "espectro-un-punto-menos.csv")

    assert pagina.get_attribute("#resultado", "data-estado") == "rechazado"
    evidencia(pagina, "t06-rechazado-simulado")


# --------------------------------------------------------------------------- #
# Fallos: 500 y sin conexión
# --------------------------------------------------------------------------- #


def prueba_un_500_muestra_el_mensaje_generico_que_manda_el_servidor(
    pagina, servidor_estatico: str
) -> None:
    cuerpo = {"titulo": "Algo falló", "mensaje": "Inténtelo más tarde.", "accion": "Avise."}
    _simular(pagina, 500, cuerpo, [])

    _abrir_y_subir(pagina, servidor_estatico)

    assert pagina.get_attribute("#resultado", "data-estado") == "error"
    assert pagina.inner_text("#resultado-mensaje") == cuerpo["mensaje"]
    assert pagina.is_disabled("#boton-analizar")


@pytest.mark.parametrize("caso", ["sin conexión", "respuesta que no es JSON"])
def prueba_sin_respuesta_util_se_avisa_sin_detalles_tecnicos(
    pagina, servidor_estatico: str, caso: str
) -> None:
    if caso == "sin conexión":
        pagina.route("**/api/validar", lambda ruta: ruta.abort("connectionrefused"))
    else:
        _simular(pagina, 502, None, [])

    _abrir_y_subir(pagina, servidor_estatico)

    texto = pagina.inner_text("#resultado")
    assert pagina.get_attribute("#resultado", "data-estado") == "error"
    assert pagina.inner_text("#resultado-accion").strip(), "todo aviso trae acción"
    for tecnico in ("TypeError", "Failed to fetch", "502", "JSON", "ERR_"):
        assert tecnico not in texto, caso
    assert pagina.is_disabled("#boton-analizar")


# --------------------------------------------------------------------------- #
# Seguridad y diseño
# --------------------------------------------------------------------------- #


def prueba_el_nombre_del_archivo_se_muestra_como_texto(
    pagina, servidor_estatico: str
) -> None:
    """Un nombre con HTML no se interpreta (todo va por textContent)."""
    malicioso = '<img src=x onerror="window.__inyectado=1">.jdx'
    _simular(pagina, 200, {"valido": True, "nombre": malicioso, "bytes": 1}, [])

    _abrir_y_subir(pagina, servidor_estatico)

    assert pagina.inner_text("#resultado-nombre") == malicioso
    assert pagina.query_selector("#resultado img") is None
    assert pagina.evaluate("window.__inyectado") is None


@pytest.mark.parametrize("estado", ["inicial", "aceptado", "rechazado"])
def prueba_a_360_px_no_hay_desplazamiento_horizontal(
    pagina, servidor_estatico: str, estado: str
) -> None:
    if estado == "inicial":
        pagina.goto(servidor_estatico + RUTA_PAGINA)
    else:
        cuerpo = (
            {"valido": True, "nombre": "a" * 200 + ".jdx", "bytes": 1}
            if estado == "aceptado"
            else _rechazo_de_ut02(mensajes.ESTRUCTURA_INVALIDA)
        )
        _simular(pagina, 200, cuerpo, [])
        _abrir_y_subir(pagina, servidor_estatico)

    ancho = pagina.evaluate("document.documentElement.scrollWidth")
    assert ancho <= 360, f"la página mide {ancho} px de ancho en un celular de 360"


def prueba_la_interfaz_no_repite_valores_de_ut03() -> None:
    """Regla 1 de CLAUDE.md, también para el frontend: formatos, tamaño,
    puntos y rango los aplica el servidor."""
    configuracion = obtener_configuracion()
    desde, hasta = configuracion.validacion.rango_requerido_cm1
    prohibidos = [
        *configuracion.archivo.formatos_permitidos,
        str(configuracion.archivo.tamano_maximo_bytes),
        f"{configuracion.archivo.tamano_maximo_bytes // (1024 * 1024)} MB",
        f"{configuracion.validacion.puntos_minimos} puntos",
        f"{desde:g}",
        f"{hasta:g}",
    ]
    hallazgos = []
    for archivo in sorted(CARPETA_FRONTEND.rglob("*")):
        if archivo.suffix not in {".html", ".js", ".css"}:
            continue
        texto = archivo.read_text(encoding="utf-8")
        for valor in prohibidos:
            if re.search(re.escape(valor), texto):
                hallazgos.append(f"{archivo.relative_to(RAIZ).as_posix()}: {valor}")

    assert not hallazgos, "valores de UT-03 escritos en la interfaz:\n" + "\n".join(
        hallazgos
    )
