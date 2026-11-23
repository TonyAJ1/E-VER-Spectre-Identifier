"""Pruebas de T-19: sin detecciones confiables y fallo del motor.

CA-08.1: con un espectro ruidoso en el que nada llega al 60 % se muestra «No
se encontraron detecciones confiables», se sugiere revisar la calidad y no se
lista ningún grupo. CA-08.2: si el mejor grupo llega a 59 % también sale el
aviso. CA-08.3: un espectro que solo tiene línea base no detiene nada.
CA-05.4: si el motor falla, se muestra «No fue posible completar el análisis;
intenta de nuevo» sin detalles técnicos y el archivo sigue cargado.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api import analisis as modulo_analisis
from backend.api.aplicacion import crear_aplicacion
from backend.api.analisis import RUTA_ANALIZAR
from backend.pruebas.apoyo_navegador import subir_en_la_pagina
from backend.utilerias import mensajes
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.inferencia.fusion import fusionar
from motor_identificacion.pruebas import espectros_simulados as sim
from motor_identificacion.reglas.via_reglas import Evaluacion


@pytest.fixture(scope="module")
def cliente():
    with TestClient(crear_aplicacion(), raise_server_exceptions=False) as cliente_http:
        yield cliente_http


def _enviar(cliente, eje, intensidad):
    return cliente.post(RUTA_ANALIZAR, json={"eje_cm1": eje, "intensidad": intensidad})


def _assert_aviso(cuerpo) -> None:
    esperado = mensajes.obtener(mensajes.SIN_DETECCIONES)
    assert cuerpo["sin_detecciones"] is True
    assert cuerpo["detecciones"] == []
    assert cuerpo["aviso"]["titulo"] == "No se encontraron detecciones confiables"
    assert cuerpo["aviso"]["mensaje"] == esperado.texto
    assert "calidad del espectro" in cuerpo["aviso"]["accion"]


def prueba_ca_08_1_el_espectro_ruidoso_da_el_aviso_y_ningun_grupo(cliente) -> None:
    eje, intensidad = sim.espectro([(2000, 0.0, 10)], ruido=0.05)
    _assert_aviso(_enviar(cliente, eje, intensidad).json())


def prueba_ca_08_2_si_el_mejor_llega_a_59_sale_el_aviso() -> None:
    motor = obtener_configuracion().motor
    resultado = fusionar(
        [Evaluacion("GF-05", round(motor.umbral_confianza - 0.01, 4), 1715.0)],
        None,
        obtener_catalogo().grupos,
        umbral=motor.umbral_confianza,
        peso_reglas=1.0,
        peso_ml=0.0,
    )
    assert resultado["sin_detecciones"] is True


def prueba_ca_08_3_solo_linea_base_no_se_detiene(cliente) -> None:
    eje = sim.eje()
    linea_base = [((4000 - x) / 3600) ** 2 for x in eje]

    respuesta = _enviar(cliente, eje, linea_base)

    assert respuesta.status_code == 200
    _assert_aviso(respuesta.json())


def prueba_ca_05_4_el_fallo_del_motor_da_el_mensaje_generico(
    cliente, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fallar(*args, **kwargs):
        raise RuntimeError("detalle interno que nadie debe ver")

    monkeypatch.setattr(modulo_analisis, "identificar", fallar)
    eje, intensidad = sim.espectro(sim.CETONA)

    respuesta = _enviar(cliente, eje, intensidad)

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert cuerpo["mensaje"] == "No fue posible completar el análisis; intenta de nuevo"
    assert "RuntimeError" not in respuesta.text
    assert "detalle interno" not in respuesta.text


@pytest.mark.parametrize(
    "cuerpo",
    [None, {"eje_cm1": [1, 2, 3], "intensidad": [1, 2, 3]}, {"eje_cm1": "x"}],
)
def prueba_un_cuerpo_que_no_es_el_vector_da_el_mismo_mensaje(cliente, cuerpo) -> None:
    respuesta = cliente.post(RUTA_ANALIZAR, json=cuerpo)
    assert respuesta.status_code == 400
    assert respuesta.json()["mensaje"] == mensajes.obtener(mensajes.ANALISIS_FALLIDO).texto


def prueba_la_api_no_recibe_archivos_solo_el_vector(cliente) -> None:
    """MOD-06 está aislado: la ruta no acepta un archivo."""
    respuesta = cliente.post(RUTA_ANALIZAR, files={"archivo": ("a.csv", b"1,2\n")})
    assert respuesta.status_code == 400


# En la página


def prueba_ca_05_4_en_la_pagina_el_archivo_sigue_cargado_para_reintentar(
    pagina, servidor: str, carpeta_fixtures, evidencia
) -> None:
    subir_en_la_pagina(
        pagina, servidor, carpeta_fixtures / "espectro-valido.jdx", "espectro.jdx"
    )
    fallo = mensajes.obtener(mensajes.ANALISIS_FALLIDO)
    pagina.route(
        "**/api/analizar",
        lambda ruta: ruta.fulfill(
            status=500,
            content_type="application/json",
            body=(
                '{"titulo": "%s", "mensaje": "%s", "accion": "%s"}'
                % (fallo.titulo, fallo.texto, fallo.accion)
            ),
        ),
    )

    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'error'"
    )

    assert pagina.inner_text("#analisis-mensaje") == fallo.texto
    assert pagina.evaluate("document.getElementById('archivo').files.length") == 1
    assert pagina.is_enabled("#boton-analizar")
    assert pagina.is_visible("#grafica canvas")
    evidencia(pagina, "t19-ca-05-4-fallo-del-motor")


def prueba_ca_08_1_en_la_pagina_sale_el_aviso_sin_lista(
    pagina, servidor: str, tmp_path, evidencia
) -> None:
    eje, intensidad = sim.espectro([(2000, 0.0, 10)], ruido=0.05)
    ruta = tmp_path / "ruidoso.csv"
    filas = ["numero de onda,absorbancia"] + [
        f"{x:.4f},{y:.6f}" for x, y in zip(eje, intensidad)
    ]
    ruta.write_text("\n".join(filas) + "\n", encoding="ascii")

    subir_en_la_pagina(pagina, servidor, ruta, "ruidoso.csv")
    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'sin-detecciones'"
    )

    assert pagina.inner_text("#analisis-titulo") == "No se encontraron detecciones confiables"
    assert pagina.locator(".deteccion").count() == 0
    evidencia(pagina, "t19-ca-08-1-sin-detecciones")
