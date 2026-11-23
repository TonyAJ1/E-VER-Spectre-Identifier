"""Pruebas de T-05 · MOD-03 · ¿el espectro cumple los requisitos?

T-04 contesta «¿es de verdad este formato?»; T-05 contesta «¿tiene los puntos y
el rango que pide UT-03?». Es una **lectura ligera**: contar pares y mirar el
mínimo y el máximo del número de onda. No se normaliza, no se ordena y no se
descomprime nada (eso es MOD-04, incremento 2).

Criterios que cubre (sección 10 del plan del incremento 1):

- **CA-02.1** · CSV de 2 columnas, 900 puntos, 400–4000 → válido.
- **CA-02.3** · espectro que solo cubre 1500–3700 → «Se requiere cubrir al menos
  1400–3700 cm⁻¹».
- **CA-02.6** · 300 puntos → válido; 299 → «Mínimo 300 puntos».

Los valores 300 y 1400–3700 **no aparecen en este archivo** como reglas: se leen
de UT-03, y hay pruebas que cambian la configuración para demostrar que el
comportamiento la sigue.
"""

from __future__ import annotations

import dataclasses
import logging
from pathlib import Path

import pytest

from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion
from backend.validacion import (
    CAPA_ESTRUCTURA,
    CAPA_PUNTOS,
    CAPA_RANGO,
    revisar_formato,
    validar,
)
from herramientas.generador_espectros import csv_sintetico, jdx_sintetico

# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #


def _texto(ruta: Path) -> str:
    """Lee un fixture igual que lo entregaría MOD-02: texto, sin BOM."""
    return ruta.read_bytes().decode("utf-8-sig", errors="replace")


def _parametros() -> Configuracion:
    return obtener_configuracion()


def _minimo() -> int:
    return _parametros().validacion.puntos_minimos


def _rango() -> tuple[float, float]:
    desde, hasta = _parametros().validacion.rango_requerido_cm1
    return float(desde), float(hasta)


def _con_validacion(**cambios: object) -> Configuracion:
    """La configuración real con otros valores de `validacion.*`."""
    configuracion = obtener_configuracion()
    return dataclasses.replace(
        configuracion,
        validacion=dataclasses.replace(configuracion.validacion, **cambios),
    )


def _csv(puntos: int, desde: float, hasta: float) -> str:
    return csv_sintetico(puntos, desde, hasta).decode("ascii")


def _jdx(puntos: int, desde: float, hasta: float) -> str:
    return jdx_sintetico("PRUEBA", puntos, desde, hasta).decode("ascii")


# --------------------------------------------------------------------------- #
# CA-02.1 · normal · CSV de 900 puntos, 400–4000 → válido
# --------------------------------------------------------------------------- #


def prueba_ca_02_1_csv_de_900_puntos_de_400_a_4000_es_valido(
    carpeta_fixtures: Path,
) -> None:
    veredicto = validar(
        "espectro.csv", _texto(carpeta_fixtures / "espectro-valido-900-puntos.csv")
    )

    assert veredicto.valido, veredicto.detalle
    assert veredicto.codigo is None


def prueba_el_jdx_valido_de_ca_01_1_cumple_puntos_y_rango(
    carpeta_fixtures: Path,
) -> None:
    veredicto = validar(
        "espectro.jdx", _texto(carpeta_fixtures / "espectro-valido.jdx")
    )

    assert veredicto.valido, veredicto.detalle


# --------------------------------------------------------------------------- #
# CA-02.6 · límite · 300 puntos → válido; 299 → «Mínimo 300 puntos»
# --------------------------------------------------------------------------- #


def prueba_ca_02_6_con_los_puntos_minimos_es_valido(carpeta_fixtures: Path) -> None:
    veredicto = validar(
        "espectro.csv", _texto(carpeta_fixtures / "espectro-puntos-minimos.csv")
    )

    assert veredicto.valido, veredicto.detalle


def prueba_ca_02_6_con_un_punto_menos_se_rechaza(carpeta_fixtures: Path) -> None:
    veredicto = validar(
        "espectro.csv", _texto(carpeta_fixtures / "espectro-un-punto-menos.csv")
    )

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.PUNTOS_INSUFICIENTES
    assert veredicto.capa == CAPA_PUNTOS


def prueba_ca_02_6_el_mensaje_es_el_literal(carpeta_fixtures: Path) -> None:
    veredicto = validar(
        "espectro.csv", _texto(carpeta_fixtures / "espectro-un-punto-menos.csv")
    )
    mensaje = mensajes.obtener(veredicto.codigo)

    assert mensaje.texto == f"Mínimo {_minimo()} puntos"
    assert mensaje.accion.strip()


@pytest.mark.parametrize("formato", ["csv", "jdx"])
def prueba_ca_02_6_la_frontera_exacta_en_los_dos_formatos(formato: str) -> None:
    """El mínimo entra; uno menos no. Igual en `.csv` que en `.jdx`."""
    armar = _csv if formato == "csv" else _jdx
    desde, hasta = 400.0, 4000.0

    justo = validar(f"e.{formato}", armar(_minimo(), desde, hasta))
    corto = validar(f"e.{formato}", armar(_minimo() - 1, desde, hasta))

    assert justo.valido, justo.detalle
    assert not corto.valido
    assert corto.codigo == mensajes.PUNTOS_INSUFICIENTES


def prueba_el_minimo_de_puntos_sale_de_ut03(carpeta_fixtures: Path) -> None:
    """Prueba de que UT-03 sirve de verdad (T-01): 300 → 500 sin tocar código."""
    contenido = _texto(carpeta_fixtures / "espectro-puntos-minimos.csv")
    exigente = _con_validacion(puntos_minimos=_minimo() + 200)

    assert validar("e.csv", contenido).valido
    rechazo = validar("e.csv", contenido, configuracion=exigente)
    assert rechazo.codigo == mensajes.PUNTOS_INSUFICIENTES
    assert mensajes.obtener(rechazo.codigo, exigente).texto == (
        f"Mínimo {_minimo() + 200} puntos"
    )


def prueba_el_encabezado_y_las_lineas_en_blanco_no_cuentan_como_puntos() -> None:
    filas = _csv(_minimo() - 1, 400.0, 4000.0).replace("\n", "\n\n")
    contenido = "onda,intensidad\n" + filas

    veredicto = validar("e.csv", contenido)

    assert veredicto.codigo == mensajes.PUNTOS_INSUFICIENTES


# --------------------------------------------------------------------------- #
# CA-02.3 · límite · solo cubre 1500–3700 → «Se requiere cubrir al menos …»
# --------------------------------------------------------------------------- #


def prueba_ca_02_3_el_rango_corto_se_rechaza(carpeta_fixtures: Path) -> None:
    veredicto = validar(
        "espectro.csv", _texto(carpeta_fixtures / "espectro-rango-corto.csv")
    )

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.RANGO_INSUFICIENTE
    assert veredicto.capa == CAPA_RANGO


def prueba_ca_02_3_el_mensaje_es_el_literal(carpeta_fixtures: Path) -> None:
    veredicto = validar(
        "espectro.csv", _texto(carpeta_fixtures / "espectro-rango-corto.csv")
    )
    mensaje = mensajes.obtener(veredicto.codigo)
    desde, hasta = _rango()

    assert mensaje.texto == f"Se requiere cubrir al menos {desde:g}–{hasta:g} cm⁻¹"
    assert mensaje.accion.strip()


@pytest.mark.parametrize("formato", ["csv", "jdx"])
@pytest.mark.parametrize(
    ("caso", "corrimiento_bajo", "corrimiento_alto", "valido"),
    [
        ("cubre justo el rango", 0.0, 0.0, True),
        ("le falta abajo (1500–3700, el de CA-02.3)", 100.0, 0.0, False),
        ("le falta arriba", 0.0, -1.0, False),
        ("le falta abajo por poco", 0.5, 0.0, False),
    ],
)
def prueba_ca_02_3_las_fronteras_del_rango(
    formato: str,
    caso: str,
    corrimiento_bajo: float,
    corrimiento_alto: float,
    valido: bool,
) -> None:
    desde, hasta = _rango()
    armar = _csv if formato == "csv" else _jdx
    contenido = armar(900, desde + corrimiento_bajo, hasta + corrimiento_alto)

    veredicto = validar(f"e.{formato}", contenido)

    assert veredicto.valido is valido, f"{caso}: {veredicto.detalle}"
    if not valido:
        assert veredicto.codigo == mensajes.RANGO_INSUFICIENTE, caso


def prueba_el_eje_descendente_tambien_cubre_el_rango() -> None:
    """Muchos equipos exportan de 4000 a 400: se mira el mínimo y el máximo,
    no el primero y el último."""
    assert validar("e.csv", _csv(900, 4000.0, 400.0)).valido
    assert validar("e.jdx", _jdx(900, 4000.0, 400.0)).valido


def prueba_el_rango_sale_de_ut03() -> None:
    contenido = _csv(900, 1500.0, 3700.0)
    flexible = _con_validacion(rango_requerido_cm1=(1500, 3700))

    assert not validar("e.csv", contenido).valido
    assert validar("e.csv", contenido, configuracion=flexible).valido


def prueba_con_pocos_puntos_y_rango_corto_se_avisa_primero_de_los_puntos() -> None:
    """Un solo mensaje por rechazo; el orden de las capas lo decide."""
    veredicto = validar("e.csv", _csv(_minimo() - 1, 1500.0, 3700.0))

    assert veredicto.codigo == mensajes.PUNTOS_INSUFICIENTES


# --------------------------------------------------------------------------- #
# CSV · se recorren todas las filas (T-04 solo miró las primeras)
# --------------------------------------------------------------------------- #


def prueba_la_basura_al_final_del_csv_se_rechaza() -> None:
    """T-04 deja pasar esto porque solo mira las primeras filas; T-05 no."""
    contenido = _csv(900, 400.0, 4000.0) + "esto no es un par\n"

    assert revisar_formato("e.csv", contenido).valido, "T-04 no llega hasta el final"
    veredicto = validar("e.csv", contenido)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA
    assert veredicto.capa == CAPA_ESTRUCTURA


def prueba_un_numero_de_onda_negativo_al_final_se_rechaza() -> None:
    contenido = _csv(900, 400.0, 4000.0) + "-10.0,0.5\n"

    veredicto = validar("e.csv", contenido)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA


def prueba_el_csv_con_punto_y_coma_y_coma_decimal_se_mide_bien() -> None:
    """`400,0;0,8` es 400.0 cm⁻¹, no 400: la coma decimal se respeta."""
    filas = _csv(900, 400.0, 4000.0)
    contenido = filas.replace(",", ";").replace(".", ",")

    assert validar("e.csv", contenido).valido


# --------------------------------------------------------------------------- #
# JCAMP-DX · solo el encabezado; sin NPOINTS/FIRSTX/LASTX falla cerrado
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("etiqueta", ["##NPOINTS=", "##FIRSTX=", "##LASTX="])
def prueba_el_jdx_sin_las_etiquetas_de_t05_falla_cerrado(etiqueta: str) -> None:
    lineas = _jdx(900, 400.0, 4000.0).splitlines(keepends=True)
    contenido = "".join(linea for linea in lineas if not linea.startswith(etiqueta))

    veredicto = validar("e.jdx", contenido)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA
    assert veredicto.capa == CAPA_ESTRUCTURA


@pytest.mark.parametrize(
    ("caso", "original", "cambio"),
    [
        ("NPOINTS no es número", "##NPOINTS=900", "##NPOINTS=muchos"),
        ("NPOINTS cero", "##NPOINTS=900", "##NPOINTS=0"),
        ("FIRSTX vacío", "##FIRSTX=400.0000", "##FIRSTX="),
        ("LASTX infinito", "##LASTX=4000.0000", "##LASTX=inf"),
    ],
)
def prueba_el_jdx_con_valores_ilegibles_falla_cerrado(
    caso: str, original: str, cambio: str
) -> None:
    contenido = _jdx(900, 400.0, 4000.0).replace(original, cambio)

    veredicto = validar("e.jdx", contenido)

    assert not veredicto.valido, caso
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA, caso


def prueba_el_jdx_se_juzga_por_el_encabezado_no_por_los_datos() -> None:
    """No se descomprime XYDATA: si el encabezado dice 299, se rechaza aunque
    haya 900 líneas de datos (el conteo real es trabajo de MOD-04)."""
    contenido = _jdx(900, 400.0, 4000.0).replace(
        "##NPOINTS=900", f"##NPOINTS={_minimo() - 1}"
    )

    assert validar("e.jdx", contenido).codigo == mensajes.PUNTOS_INSUFICIENTES


def prueba_las_etiquetas_del_jdx_se_leen_como_dice_el_estandar() -> None:
    """JCAMP-DX compara etiquetas sin mayúsculas, espacios ni guiones, y los
    comentarios `$$` al final de la línea no son parte del valor."""
    contenido = (
        _jdx(900, 400.0, 4000.0)
        .replace("##NPOINTS=900", "##N Points= 900 $$ conteo")
        .replace("##FIRSTX=400.0000", "##first_x=400.0")
    )

    assert validar("e.jdx", contenido).valido


def prueba_las_etiquetas_despues_de_los_datos_no_cuentan() -> None:
    """Solo vale el encabezado: lo que venga después de XYDATA no se lee."""
    lineas = _jdx(900, 400.0, 4000.0).replace("##NPOINTS=900\n", "")
    contenido = lineas.replace("##END=", "##NPOINTS=900\n##END=")

    veredicto = validar("e.jdx", contenido)

    assert veredicto.capa == CAPA_ESTRUCTURA


# --------------------------------------------------------------------------- #
# La frontera con T-04 y los registros
# --------------------------------------------------------------------------- #


def prueba_revisar_formato_no_aplica_puntos_ni_rango(carpeta_fixtures: Path) -> None:
    """La separación clave del plan: T-04 no cuenta, T-05 sí."""
    for archivo in ("espectro-un-punto-menos.csv", "espectro-rango-corto.csv"):
        contenido = _texto(carpeta_fixtures / archivo)
        assert revisar_formato(archivo, contenido).valido
        assert not validar(archivo, contenido).valido


def prueba_un_fallo_de_formato_no_llega_a_t05() -> None:
    veredicto = validar("e.csv", "")

    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA


def prueba_el_registro_de_t05_no_guarda_el_contenido(
    caplog: pytest.LogCaptureFixture,
) -> None:
    contenido = _csv(_minimo() - 1, 400.0, 4000.0)

    with caplog.at_level(logging.INFO):
        veredicto = validar("acetona.csv", contenido)

    registrado = "\n".join(r.getMessage() for r in caplog.records)
    assert veredicto.codigo == mensajes.PUNTOS_INSUFICIENTES
    assert mensajes.PUNTOS_INSUFICIENTES in registrado
    assert "0.800000" not in registrado, "el contenido nunca va al registro (RNF-09)"


def prueba_el_tamano_maximo_tambien_pasa_t05(csv_tamano_maximo: Path) -> None:
    """El archivo de CA-01.2 trae puntos y rango suficientes: 5 MB completos."""
    veredicto = validar("maximo.csv", _texto(csv_tamano_maximo))

    assert veredicto.valido, veredicto.detalle
