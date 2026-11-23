"""Pruebas de T-18: ordenar los resultados y mostrarlos con su confianza.

CA-05.1 pide que con el espectro de referencia de la acetona se detecte C=O
con al menos 60 %, en porcentaje. CA-05.2 pide que con el del ácido benzoico
aparezcan O–H, C=O y anillo aromático, de mayor a menor confianza. Esos dos
espectros son los reales de NIST y no se pueden guardar en el repositorio:
las pruebas se saltan si no están en datos/referencia.

Para no depender de ellos, el mismo camino se prueba con espectros simulados
que pasan por la API y por la página de verdad.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.aplicacion import crear_aplicacion
from backend.api.analisis import RUTA_ANALIZAR, analizar_espectro
from backend.preprocesamiento.procesador import procesar
from backend.pruebas.apoyo_navegador import subir_en_la_pagina
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.pruebas import espectros_simulados as sim

RAIZ = Path(__file__).resolve().parents[2]
MANIFIESTO = RAIZ / "herramientas" / "espectros_nist.json"


@pytest.fixture(scope="module")
def cliente():
    with TestClient(crear_aplicacion()) as cliente_http:
        yield cliente_http


def _analizar(cliente, bandas):
    eje, intensidad = sim.espectro(bandas)
    return cliente.post(RUTA_ANALIZAR, json={"eje_cm1": eje, "intensidad": intensidad})


def _real(nombre_archivo: str):
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    ruta = RAIZ / manifiesto["carpeta_destino"] / nombre_archivo
    if not ruta.is_file():
        pytest.skip(
            f"falta {nombre_archivo} en datos/referencia; bájelo con "
            "python -m herramientas.descargar_espectros_nist"
        )
    resultado = procesar(nombre_archivo, ruta.read_text(encoding="latin-1"))
    assert resultado.valido, resultado.detalle
    espectro = resultado.espectro
    return analizar_espectro(
        list(espectro.eje_cm1),
        list(espectro.intensidad),
        obtener_configuracion(),
        obtener_catalogo(),
    )


# Con los espectros reales de NIST


def prueba_ca_05_1_la_acetona_real_da_c_o_con_al_menos_60() -> None:
    resultado = _real("67-64-1-IR.jdx")
    carbonilo = next(d for d in resultado["detecciones"] if d["grupo"] == "GF-05")
    assert carbonilo["porcentaje"] >= obtener_configuracion().motor.umbral_confianza * 100


def prueba_ca_05_2_el_acido_benzoico_real_lista_o_h_c_o_y_aromatico() -> None:
    resultado = _real("65-85-0-IR.jdx")
    grupos = [d["grupo"] for d in resultado["detecciones"]]
    assert {"GF-01", "GF-05", "GF-07"} <= set(grupos)
    confianzas = [d["confianza"] for d in resultado["detecciones"]]
    assert confianzas == sorted(confianzas, reverse=True)


# Con espectros simulados por la API


def prueba_la_cetona_simulada_da_c_o_en_porcentaje(cliente) -> None:
    cuerpo = _analizar(cliente, sim.CETONA).json()

    carbonilo = next(d for d in cuerpo["detecciones"] if d["grupo"] == "GF-05")
    assert carbonilo["nombre"] == obtener_catalogo().grupo("GF-05").nombre
    assert carbonilo["porcentaje"] == round(carbonilo["confianza"] * 100, 1)
    assert carbonilo["porcentaje"] >= 60


def prueba_el_acido_aromatico_simulado_lista_sus_tres_grupos_en_orden(cliente) -> None:
    cuerpo = _analizar(cliente, sim.ACIDO_AROMATICO).json()

    grupos = [d["grupo"] for d in cuerpo["detecciones"]]
    assert {"GF-01", "GF-05", "GF-07"} <= set(grupos)
    confianzas = [d["confianza"] for d in cuerpo["detecciones"]]
    assert confianzas == sorted(confianzas, reverse=True)


# En la página


def _csv_simulado(tmp_path: Path, bandas) -> Path:
    eje, intensidad = sim.espectro(bandas)
    ruta = tmp_path / "simulado.csv"
    filas = ["numero de onda,absorbancia"] + [
        f"{x:.4f},{y:.6f}" for x, y in zip(eje, intensidad)
    ]
    ruta.write_text("\n".join(filas) + "\n", encoding="ascii")
    return ruta


def prueba_ca_05_1_en_la_pagina_aparece_c_o_con_su_porcentaje(
    pagina, servidor: str, tmp_path: Path, evidencia
) -> None:
    subir_en_la_pagina(pagina, servidor, _csv_simulado(tmp_path, sim.CETONA), "cetona.csv")
    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'detecciones'"
    )

    nombres = pagina.locator(".deteccion-nombre").all_inner_texts()
    porcentajes = pagina.locator(".deteccion-confianza").all_inner_texts()
    assert obtener_catalogo().grupo("GF-05").nombre in nombres
    assert all(texto.endswith(" %") for texto in porcentajes)
    valores = [float(t.replace(" %", "").replace(",", ".")) for t in porcentajes]
    assert valores == sorted(valores, reverse=True)
    evidencia(pagina, "t18-ca-05-1-lista")
