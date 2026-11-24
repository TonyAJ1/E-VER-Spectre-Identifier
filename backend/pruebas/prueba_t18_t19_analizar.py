"""T-18 y T-19: POST /api/analizar, la lista con su confianza y los avisos.

Se prueba de punta a punta con la aplicación real: primero /api/procesar con
un CSV fabricado aquí mismo y después /api/analizar con el espectro que
devolvió. Así se cubre exactamente lo que hace la página.

Los espectros fabricados no reemplazan a los de referencia. CA-05.1 y CA-05.2
piden la acetona y el ácido benzoico reales, que viven fuera del repositorio
(datos/referencia); esas pruebas se saltan si el archivo no está, igual que
las de T-15.

Dos criterios quedan marcados como fallo esperado, con su motivo: CA-08.1
(espectro ruidoso) y CA-08.3 (solo línea base). La vía de reglas, tal como
quedó calibrada en T-15d, reporta grupos sobre ruido puro y sobre una línea
base inclinada. Es la debilidad de los pisos de D-22 que el traspaso del
incremento 3 ya sospechaba. La regla del equipo es no mover un umbral para
que pase una prueba, así que el fallo se deja escrito y la marca se quita
cuando el motor acierte.
"""

from __future__ import annotations

import logging
import math
import random
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api import RUTA_ANALIZAR, RUTA_PROCESAR, crear_aplicacion
from backend.api import aplicacion as capa_http
from motor_identificacion.inferencia.red import ARCHIVO_PESOS
from backend.utilerias import mensajes
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.inferencia import MODO_HIBRIDO, MODO_REGLAS
from motor_identificacion.reglas import ErrorDelMotor

RAIZ = Path(__file__).resolve().parents[2]
REFERENCIA = RAIZ / "datos" / "referencia"


@pytest.fixture(scope="module")
def cliente() -> TestClient:
    with TestClient(crear_aplicacion()) as abierto:
        yield abierto


def _csv(funcion: Callable[[float], float]) -> bytes:
    """Un CSV de absorbancia de 4000 a 400 cm⁻¹, cada 2 cm⁻¹."""
    filas = ["numero_de_onda,absorbancia"]
    onda = 4000.0
    while onda >= 400:
        filas.append(f"{onda:.1f},{funcion(onda):.6f}")
        onda -= 2
    return "\n".join(filas).encode("utf-8")


def _banda(onda: float, centro: float, altura: float, ancho: float) -> float:
    sigma = ancho / (2 * math.sqrt(2 * math.log(2)))
    return altura * math.exp(-((onda - centro) ** 2) / (2 * sigma**2))


def _carbonilo(onda: float) -> float:
    """Una cetona de mentira: C=O fuerte en 1715 y C–H alifático débil."""
    return (
        0.02
        + _banda(onda, 1715, 1.0, 20)
        + _banda(onda, 2950, 0.3, 15)
        + _banda(onda, 2870, 0.2, 15)
    )


def _procesar(cliente: TestClient, nombre: str, contenido: bytes) -> dict:
    respuesta = cliente.post(
        RUTA_PROCESAR, files={"archivo": (nombre, contenido, "text/csv")}
    )
    datos = respuesta.json()
    assert datos["valido"], datos
    return datos


def _analizar(cliente: TestClient, espectro: dict):
    return cliente.post(RUTA_ANALIZAR, json=espectro)


# T-18: la lista


def prueba_un_carbonilo_sale_detectado_con_su_porcentaje(cliente) -> None:
    espectro = _procesar(cliente, "cetona.csv", _csv(_carbonilo))["espectro"]

    respuesta = _analizar(cliente, espectro)
    datos = respuesta.json()

    assert respuesta.status_code == 200
    assert datos["valido"] is True
    assert datos["sin_detecciones"] is False
    assert "aviso" not in datos
    primera = datos["detecciones"][0]
    assert primera["grupo"] == "GF-05"
    assert primera["nombre"]
    assert primera["porcentaje"] >= 60
    assert 1670 <= primera["pico_cm1"] <= 1780
    assert primera["region_cm1"] == [1670, 1780]


def prueba_la_respuesta_trae_las_llaves_del_contrato_de_mod06(cliente) -> None:
    espectro = _procesar(cliente, "cetona.csv", _csv(_carbonilo))["espectro"]

    datos = _analizar(cliente, espectro).json()

    assert set(datos) == {"valido", "detecciones", "sin_detecciones", "umbral", "modo"}
    assert set(datos["detecciones"][0]) == {
        "grupo", "nombre", "confianza", "porcentaje", "region_cm1", "pico_cm1", "evidencia",
        # Agregada en el incremento 4 por MOD-07.
        "explicacion",
    }
    assert set(datos["detecciones"][0]["evidencia"]) == {"regla", "ml"}
    assert datos["umbral"] == obtener_configuracion().motor.umbral_confianza


def prueba_el_porcentaje_es_el_de_la_confianza(cliente) -> None:
    """D-15: lo que se ve sale del mismo número con que se decidió."""
    espectro = _procesar(cliente, "cetona.csv", _csv(_carbonilo))["espectro"]

    for deteccion in _analizar(cliente, espectro).json()["detecciones"]:
        assert deteccion["porcentaje"] == round(deteccion["confianza"] * 100)


def prueba_la_lista_va_de_mayor_a_menor(cliente) -> None:
    espectro = _procesar(cliente, "cetona.csv", _csv(_carbonilo))["espectro"]

    confianzas = [d["confianza"] for d in _analizar(cliente, espectro).json()["detecciones"]]

    assert confianzas == sorted(confianzas, reverse=True)


def prueba_sin_modelo_entrenado_el_motor_trabaja_solo_con_reglas(cliente, caplog) -> None:
    """D-16.4: la falta de modelo se anota en el registro y no es un error.

    Desde T-16c la aplicación carga la red del repositorio por omisión; aquí
    se le pide explícitamente que arranque sin ella.
    """
    with caplog.at_level(logging.INFO):
        with TestClient(crear_aplicacion(modelo=None)) as nuevo:
            espectro = _procesar(nuevo, "cetona.csv", _csv(_carbonilo))["espectro"]
            datos = _analizar(nuevo, espectro).json()

    assert datos["modo"] == MODO_REGLAS
    assert all(d["evidencia"]["ml"] is None for d in datos["detecciones"])
    assert any("modo=reglas" in r.getMessage() for r in caplog.records)


def prueba_con_un_modelo_la_aplicacion_trabaja_en_modo_hibrido() -> None:
    puntos = obtener_configuracion().procesamiento.puntos_rejilla

    class Modelo:
        puntos_rejilla = puntos

        def probabilidades(self, ventana):
            return (0.9,) * 7

    with TestClient(crear_aplicacion(modelo=Modelo())) as hibrido:
        espectro = _procesar(hibrido, "cetona.csv", _csv(_carbonilo))["espectro"]
        datos = _analizar(hibrido, espectro).json()

    assert datos["modo"] == MODO_HIBRIDO
    assert all(d["evidencia"]["ml"] == 0.9 for d in datos["detecciones"])


# D-17: lo que llega se revisa antes del motor


def _espectro_bueno(cliente) -> dict:
    return _procesar(cliente, "cetona.csv", _csv(_carbonilo))["espectro"]


def _malos(bueno: dict) -> dict[str, object]:
    corto = {**bueno, "intensidad": bueno["intensidad"][:-1]}
    fuera = {**bueno, "intensidad": [2.0] + bueno["intensidad"][1:]}
    al_reves = {**bueno, "eje_cm1": list(reversed(bueno["eje_cm1"]))}
    con_texto = {**bueno, "intensidad": ["0.1"] + bueno["intensidad"][1:]}
    medido_al_reves = {**bueno, "rango_medido_cm1": [4000, 400]}
    sin_eje = {k: v for k, v in bueno.items() if k != "eje_cm1"}
    return {
        "intensidad corta": corto,
        "valor fuera de 0 a 1": fuera,
        "eje al revés": al_reves,
        "número como texto": con_texto,
        "tramo medido al revés": medido_al_reves,
        "sin eje": sin_eje,
        "una lista": [1, 2, 3],
        "nada": None,
    }


def prueba_un_vector_mal_formado_se_rechaza_sin_llegar_al_motor(cliente, monkeypatch) -> None:
    llamadas = []
    monkeypatch.setattr(capa_http, "identificar", lambda *a, **k: llamadas.append(a))
    bueno = _espectro_bueno(cliente)

    with TestClient(crear_aplicacion()) as nuevo:
        for caso, cuerpo in _malos(bueno).items():
            respuesta = nuevo.post(RUTA_ANALIZAR, json=cuerpo)
            datos = respuesta.json()
            assert respuesta.status_code == 200, caso
            assert datos["valido"] is False, caso
            assert datos["codigo"] == mensajes.ESPECTRO_INVALIDO, caso
            assert datos["accion"], caso

    assert llamadas == []


def prueba_un_cuerpo_que_no_es_json_se_rechaza(cliente) -> None:
    respuesta = cliente.post(
        RUTA_ANALIZAR, content=b"esto no es json", headers={"content-type": "application/json"}
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["codigo"] == mensajes.ESPECTRO_INVALIDO


def prueba_se_acepta_tambien_la_respuesta_entera_de_procesar(cliente) -> None:
    procesado = _procesar(cliente, "cetona.csv", _csv(_carbonilo))

    assert _analizar(cliente, procesado).json()["valido"] is True


# T-19: el fallo del motor (CA-05.4)


def prueba_ca_05_4_un_fallo_del_motor_da_el_mensaje_generico(cliente, monkeypatch) -> None:
    espectro = _espectro_bueno(cliente)

    def falla(*args, **kwargs):
        raise ErrorDelMotor("detalle interno que el usuario no debe ver")

    monkeypatch.setattr(capa_http, "identificar", falla)
    with TestClient(crear_aplicacion()) as nuevo:
        respuesta = _analizar(nuevo, espectro)

    datos = respuesta.json()
    assert respuesta.status_code == 500
    assert datos["valido"] is False
    assert datos["codigo"] == mensajes.ANALISIS_FALLIDO
    assert datos["mensaje"] == "No fue posible completar el análisis; intenta de nuevo."
    assert "interno" not in str(datos)
    assert "Error" not in str(datos)


def prueba_despues_de_un_fallo_el_servicio_sigue_de_pie(cliente, monkeypatch) -> None:
    espectro = _espectro_bueno(cliente)
    with TestClient(crear_aplicacion()) as nuevo:
        with monkeypatch.context() as cambio:
            cambio.setattr(capa_http, "identificar", lambda *a, **k: 1 / 0)
            assert _analizar(nuevo, espectro).status_code == 500
        # El mismo espectro, sin volver a subir el archivo, ya funciona.
        assert _analizar(nuevo, espectro).json()["valido"] is True


# T-19: sin detecciones confiables (CA-08)


def prueba_sin_detecciones_viaja_como_resultado_con_su_aviso(cliente, monkeypatch) -> None:
    from motor_identificacion.inferencia import ResultadoMotor

    vacio = ResultadoMotor(
        detecciones=(), umbral=0.6, modo=MODO_REGLAS, version_catalogo="x", confianzas={}
    )
    monkeypatch.setattr(capa_http, "identificar", lambda *a, **k: vacio)
    espectro = _espectro_bueno(cliente)

    with TestClient(crear_aplicacion()) as nuevo:
        respuesta = _analizar(nuevo, espectro)

    datos = respuesta.json()
    assert respuesta.status_code == 200
    assert datos["valido"] is True
    assert datos["sin_detecciones"] is True
    assert datos["detecciones"] == []
    assert datos["aviso"]["titulo"] == "No se encontraron detecciones confiables"
    assert "calidad del espectro" in datos["aviso"]["accion"]
    assert "60 %" in datos["aviso"]["mensaje"]


def _ruido(semilla: int) -> Callable[[float], float]:
    azar = random.Random(semilla)
    return lambda onda: 0.3 + 0.05 * azar.gauss(0, 1)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Hallazgo: la vía de reglas de T-15d reporta entre cinco y seis grupos "
        "sobre ruido puro (62 a 80 %), y con la red de T-16c el motor completo "
        "todavía no baja todos del umbral. No se recalibra para pasar la prueba."
    ),
)
@pytest.mark.parametrize("semilla", [1, 2, 7])
def prueba_ca_08_1_un_espectro_ruidoso_no_deja_grupos(cliente, semilla) -> None:
    espectro = _procesar(cliente, "ruido.csv", _csv(_ruido(semilla)))["espectro"]

    datos = _analizar(cliente, espectro).json()

    assert datos["sin_detecciones"] is True


@pytest.mark.parametrize(
    "linea",
    [
        pytest.param(
            lambda x: 0.1 + 0.00002 * (4000 - x),
            id="inclinada",
            marks=pytest.mark.xfail(
                strict=True,
                reason=(
                    "Hallazgo: con una línea base inclinada, la vía de reglas "
                    "reporta O–H al 100 % sin pico, y ni con la red el motor "
                    "completo baja del umbral. No se recalibra para pasar la prueba."
                ),
            ),
        ),
        pytest.param(
            lambda x: 0.1 + 0.05 * ((x - 2200) / 1800) ** 2,
            id="curva",
            # Solo con reglas también falla; con la red de T-16c el motor
            # completo ya acierta. Sin archivo de pesos vuelve el hallazgo.
            marks=pytest.mark.xfail(
                not ARCHIVO_PESOS.is_file(),
                strict=True,
                reason="sin la red, la vía de reglas reporta O–H al 100 % sin pico",
            ),
        ),
    ],
)
def prueba_ca_08_3_solo_linea_base_avisa_sin_detecciones(cliente, linea) -> None:
    espectro = _procesar(cliente, "linea.csv", _csv(linea))["espectro"]

    respuesta = _analizar(cliente, espectro)

    assert respuesta.status_code == 200
    assert respuesta.json()["sin_detecciones"] is True


def prueba_ca_08_3_la_linea_base_no_detiene_la_aplicacion(cliente) -> None:
    """La parte de CA-08.3 que sí se cumple hoy: responde sin caerse."""
    espectro = _procesar(cliente, "linea.csv", _csv(lambda x: 0.1 + 0.00002 * (4000 - x)))

    respuesta = _analizar(cliente, espectro["espectro"])

    assert respuesta.status_code == 200
    assert respuesta.json()["valido"] is True


# CA-05.1 y CA-05.2 con los espectros reales


def _real(cliente: TestClient, archivo: str) -> dict:
    ruta = REFERENCIA / archivo
    if not ruta.is_file():
        pytest.skip(
            f"falta {archivo} en datos/referencia; bájelo con "
            "«python -m herramientas.descargar_espectros_nist»"
        )
    respuesta = cliente.post(
        RUTA_PROCESAR, files={"archivo": (ruta.name, ruta.read_bytes(), "text/plain")}
    )
    datos = respuesta.json()
    if not datos.get("valido"):
        pytest.skip(f"{archivo} no pasa por /api/procesar: {datos.get('codigo')}")
    return datos["espectro"]


def prueba_ca_05_1_la_acetona_da_carbonilo_al_menos_al_60(cliente) -> None:
    datos = _analizar(cliente, _real(cliente, "67-64-1-IR.jdx")).json()

    carbonilo = [d for d in datos["detecciones"] if d["grupo"] == "GF-05"]
    assert carbonilo and carbonilo[0]["porcentaje"] >= 60


def prueba_ca_05_2_el_acido_benzoico_lista_oh_co_y_aromatico_en_orden(cliente) -> None:
    datos = _analizar(cliente, _real(cliente, "65-85-0-IR.jdx")).json()

    grupos = [d["grupo"] for d in datos["detecciones"]]
    assert {"GF-01", "GF-05", "GF-07"} <= set(grupos)
    confianzas = [d["confianza"] for d in datos["detecciones"]]
    assert confianzas == sorted(confianzas, reverse=True)
