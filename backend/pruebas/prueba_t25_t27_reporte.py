"""T-25, T-26 y T-27: el reporte en PDF.

Se prueba con la aplicación real: /api/procesar con un CSV fabricado, y luego
/api/reporte con ese espectro y una imagen PNG fabricada aquí. El PDF se lee
con pypdf para revisar su texto y sus imágenes.

CA-09.1: el PDF trae el nombre del archivo, la fecha y hora, la gráfica, cada
grupo con su confianza y explicación y el aviso de resultado orientativo.
CA-09.2: sin detecciones, el PDF lo dice explícitamente.
CA-09.3: si falla al generar, responde un mensaje de UT-02 y se puede
reintentar; los resultados de la página no dependen de esta ruta.
"""

from __future__ import annotations

import base64
import io
import math
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfReader

from backend.api import RUTA_PROCESAR, RUTA_REPORTE, crear_aplicacion
from backend.api import aplicacion as capa_http
from backend.api.entrada_reporte import peticion_desde
from backend.reportes import AVISO_ORIENTATIVO, AVISO_SOLO_REGLAS, TITULO
from backend.utilerias import mensajes
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.inferencia import ResultadoMotor
from motor_identificacion.inferencia.red import ARCHIVO_PESOS

RAIZ = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    with TestClient(crear_aplicacion()) as abierto:
        yield abierto


def _png(ancho: int = 60, alto: int = 30) -> bytes:
    salida = io.BytesIO()
    Image.new("RGB", (ancho, alto), (230, 159, 0)).save(salida, format="PNG")
    return salida.getvalue()


def _data_url(datos: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(datos).decode()


def _banda(onda, centro, altura, ancho):
    sigma = ancho / (2 * math.sqrt(2 * math.log(2)))
    return altura * math.exp(-((onda - centro) ** 2) / (2 * sigma**2))


def _csv_carbonilo() -> bytes:
    filas = ["numero_de_onda,absorbancia"]
    onda = 4000.0
    while onda >= 400:
        filas.append(f"{onda:.1f},{0.02 + _banda(onda, 1715, 1.0, 20):.6f}")
        onda -= 2
    return "\n".join(filas).encode()


def _espectro(cliente) -> dict:
    respuesta = cliente.post(
        RUTA_PROCESAR, files={"archivo": ("cetona.csv", _csv_carbonilo(), "text/csv")}
    ).json()
    assert respuesta["valido"]
    return respuesta["espectro"]


def _cuerpo(cliente, **cambios) -> dict:
    cuerpo = {
        "nombre": "cetona.csv",
        "espectro": _espectro(cliente),
        "grafica_png": _data_url(_png()),
        "zona_horaria_min": 360,
    }
    cuerpo.update(cambios)
    return cuerpo


def _texto(pdf: bytes) -> str:
    lector = PdfReader(io.BytesIO(pdf))
    return "\n".join(pagina.extract_text() for pagina in lector.pages)


def _imagenes(pdf: bytes) -> int:
    return sum(len(p.images) for p in PdfReader(io.BytesIO(pdf)).pages)


# T-25 y T-26: CA-09.1


def prueba_ca_09_1_el_pdf_trae_todo_lo_que_pide_el_criterio(cliente) -> None:
    respuesta = cliente.post(RUTA_REPORTE, json=_cuerpo(cliente))

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.content.startswith(b"%PDF")
    texto = _texto(respuesta.content)
    assert TITULO in texto
    assert "cetona.csv" in texto
    assert "Fecha y hora del análisis" in texto
    assert "UTC-06:00" in texto
    assert "C=O" in texto
    assert "% de confianza" in texto
    assert "pico intenso y agudo" in texto
    assert AVISO_ORIENTATIVO.split(".")[0] in " ".join(texto.split())


def prueba_t26_el_pdf_lleva_la_imagen_de_la_grafica(cliente) -> None:
    respuesta = cliente.post(RUTA_REPORTE, json=_cuerpo(cliente))

    assert _imagenes(respuesta.content) == 1


def prueba_una_grafica_muy_alta_cabe_en_la_hoja(cliente) -> None:
    respuesta = cliente.post(
        RUTA_REPORTE, json=_cuerpo(cliente, grafica_png=_data_url(_png(40, 1600)))
    )

    assert respuesta.status_code == 200
    assert _imagenes(respuesta.content) == 1


def prueba_sin_modelo_el_reporte_dice_que_fue_solo_con_reglas() -> None:
    with TestClient(crear_aplicacion(modelo=None)) as solo_reglas:
        respuesta = solo_reglas.post(RUTA_REPORTE, json=_cuerpo(solo_reglas))
    texto = " ".join(_texto(respuesta.content).split())

    assert AVISO_SOLO_REGLAS in texto


def prueba_con_la_red_el_reporte_no_dice_que_fue_solo_con_reglas(cliente) -> None:
    if not ARCHIVO_PESOS.is_file():
        pytest.skip("no hay red entrenada")
    texto = " ".join(_texto(cliente.post(RUTA_REPORTE, json=_cuerpo(cliente)).content).split())

    assert AVISO_SOLO_REGLAS not in texto


def prueba_el_pdf_se_descarga_con_un_nombre_seguro(cliente) -> None:
    respuesta = cliente.post(
        RUTA_REPORTE, json=_cuerpo(cliente, nombre='ácido "raro" ../x.jdx')
    )

    disposicion = respuesta.headers["content-disposition"]
    assert disposicion.startswith("attachment;")
    assert ".." not in disposicion.split("filename=")[1]
    assert disposicion.endswith('.pdf"')


def prueba_un_nombre_con_marcado_no_rompe_el_pdf(cliente) -> None:
    respuesta = cliente.post(RUTA_REPORTE, json=_cuerpo(cliente, nombre="<b>a & b</b>.csv"))

    assert respuesta.status_code == 200
    assert "<b>a & b</b>.csv" in _texto(respuesta.content)


def prueba_rnf_09_el_reporte_no_se_escribe_en_disco(cliente, monkeypatch, tmp_path) -> None:
    """Ni ReportLab ni la ruta abren archivos para escribir mientras se arma."""
    import builtins

    original = builtins.open
    escrituras = []

    def vigilado(archivo, modo="r", *args, **kwargs):
        if any(letra in modo for letra in "wax+"):
            escrituras.append(str(archivo))
        return original(archivo, modo, *args, **kwargs)

    cuerpo = _cuerpo(cliente)
    monkeypatch.setattr(builtins, "open", vigilado)
    respuesta = cliente.post(RUTA_REPORTE, json=cuerpo)

    assert respuesta.status_code == 200
    assert escrituras == []


def prueba_la_fecha_va_en_la_hora_de_quien_analizo() -> None:
    configuracion = obtener_configuracion()
    with TestClient(crear_aplicacion()) as cliente:
        cuerpo = _cuerpo(cliente)
    ahora = datetime(2026, 11, 24, 10, 30, tzinfo=timezone.utc)

    peticion = peticion_desde(cuerpo, configuracion, ahora)

    assert peticion is not None
    assert peticion.fecha_hora.hour == 4
    assert peticion.zona == "UTC-06:00"


# Lo que llega se revisa


@pytest.mark.parametrize(
    "caso, cambio",
    [
        ("sin nombre", {"nombre": ""}),
        ("nombre que no es texto", {"nombre": 5}),
        ("imagen que no es PNG", {"grafica_png": "data:image/png;base64," + base64.b64encode(b"GIF89a").decode()}),
        ("imagen sin prefijo", {"grafica_png": base64.b64encode(_png()).decode()}),
        ("imagen con base64 roto", {"grafica_png": "data:image/png;base64,@@@"}),
        ("espectro mal formado", {"espectro": {"eje_cm1": [1, 2]}}),
        ("zona horaria imposible", {"zona_horaria_min": 100000}),
    ],
)
def prueba_una_peticion_incompleta_se_rechaza(cliente, caso, cambio) -> None:
    respuesta = cliente.post(RUTA_REPORTE, json=_cuerpo(cliente, **cambio))

    assert respuesta.status_code == 200, caso
    datos = respuesta.json()
    assert datos["valido"] is False, caso
    assert datos["codigo"] == mensajes.REPORTE_INVALIDO, caso


def prueba_una_imagen_demasiado_grande_se_rechaza(cliente, monkeypatch) -> None:
    configuracion = obtener_configuracion()
    archivo = configuracion.archivo.__class__(
        tamano_maximo_bytes=100, formatos_permitidos=configuracion.archivo.formatos_permitidos
    )
    chica = configuracion.__class__(**{**configuracion.__dict__, "archivo": archivo})

    assert peticion_desde(_cuerpo(TestClient(crear_aplicacion())), chica) is None


def prueba_un_cuerpo_enorme_se_corta_sin_leerlo_entero(cliente) -> None:
    limite = obtener_configuracion().archivo.tamano_maximo_bytes * capa_http.FACTOR_CUERPO_JSON
    enorme = b'{"nombre": "' + b"a" * (limite + 10) + b'"}'

    respuesta = cliente.post(
        RUTA_REPORTE, content=enorme, headers={"content-type": "application/json"}
    )

    assert respuesta.json()["codigo"] == mensajes.REPORTE_INVALIDO


# T-27: CA-09.2 y CA-09.3


def prueba_ca_09_2_sin_detecciones_el_pdf_lo_dice(cliente, monkeypatch) -> None:
    vacio = ResultadoMotor((), 0.6, "reglas", "x", {})
    monkeypatch.setattr(capa_http, "identificar", lambda *a, **k: vacio)
    with TestClient(crear_aplicacion()) as nuevo:
        respuesta = nuevo.post(RUTA_REPORTE, json=_cuerpo(cliente))

    assert respuesta.status_code == 200
    texto = _texto(respuesta.content)
    assert "No se encontraron detecciones confiables" in texto
    assert "C=O" not in texto, "no aparece ningún grupo"


def prueba_ca_09_3_un_fallo_al_generar_da_mensaje_y_se_puede_reintentar(
    cliente, monkeypatch
) -> None:
    cuerpo = _cuerpo(cliente)
    with TestClient(crear_aplicacion()) as nuevo:
        with monkeypatch.context() as cambio:

            def falla(datos):
                raise RuntimeError("detalle interno")

            cambio.setattr(capa_http, "generar_pdf", falla)
            respuesta = nuevo.post(RUTA_REPORTE, json=cuerpo)

        datos = respuesta.json()
        assert respuesta.status_code == 500
        assert datos["codigo"] == mensajes.REPORTE_FALLIDO
        assert "Descargar reporte" in datos["accion"]
        assert "interno" not in str(datos)

        # El mismo pedido, sin volver a analizar, ya sale bien.
        assert nuevo.post(RUTA_REPORTE, json=cuerpo).status_code == 200
