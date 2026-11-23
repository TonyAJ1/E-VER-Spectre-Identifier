"""Pruebas de T-02 · UT-02 Mensajes.

Pruebas unitarias de catálogo (código → mensaje esperado), según la sección 9
del plan del incremento 1, y la condición de «terminado» de T-02:

- los cuatro textos de la sección 4 salen **literales**, porque los criterios de
  aceptación los verifican palabra por palabra;
- esos textos se arman desde UT-03: cambiar el archivo de parámetros cambia el
  mensaje, sin tocar código;
- cada código devuelve título, texto y acción (motivo + acción, RNF-01);
- ningún mensaje trae detalles técnicos;
- un código que no existe no pasa desapercibido.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from backend.utilerias import mensajes
from backend.utilerias.configuracion import (
    NOMBRE_ARCHIVO,
    RUTA_PARAMETROS,
    Configuracion,
    cargar,
)

# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #


def _configuracion_con(carpeta: Path, bloque: str, llave: str, valor: Any) -> Configuracion:
    """Una configuración igual a la del repositorio, con un valor cambiado."""
    datos = json.loads(RUTA_PARAMETROS.read_text(encoding="utf-8"))
    datos[bloque][llave] = valor
    ruta = carpeta / NOMBRE_ARCHIVO
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return cargar(ruta)


# --------------------------------------------------------------------------- #
# Sección 4 · los cuatro textos exigidos
# --------------------------------------------------------------------------- #


def prueba_formato_no_soportado_ca_01_3() -> None:
    mensaje = mensajes.obtener(mensajes.FORMATO_NO_SOPORTADO)

    assert mensaje.texto == "Formato no soportado. Formatos admitidos: .jdx, .csv"


def prueba_tamano_excedido_ca_02_2() -> None:
    mensaje = mensajes.obtener(mensajes.TAMANO_EXCEDIDO)

    assert mensaje.texto == "El tamaño máximo permitido es de 5 MB"


def prueba_rango_insuficiente_ca_02_3() -> None:
    mensaje = mensajes.obtener(mensajes.RANGO_INSUFICIENTE)

    assert mensaje.texto == "Se requiere cubrir al menos 1400–3700 cm⁻¹"


def prueba_puntos_insuficientes_ca_02_6() -> None:
    mensaje = mensajes.obtener(mensajes.PUNTOS_INSUFICIENTES)

    assert mensaje.texto == "Mínimo 300 puntos"


# --------------------------------------------------------------------------- #
# Los textos se arman desde UT-03, no están escritos a mano
# --------------------------------------------------------------------------- #


def prueba_la_lista_de_formatos_sale_de_ut03(tmp_path: Path) -> None:
    """El tercer formato es inventado a propósito: lo que se prueba es que el
    mensaje repita la lista de UT-03, no que la aplicación admita ese formato.
    Hoy solo se admiten `.jdx` y `.csv` (D-0)."""
    configuracion = _configuracion_con(
        tmp_path, "archivo", "formatos_permitidos", [".jdx", ".csv", ".abc"]
    )

    mensaje = mensajes.obtener(mensajes.FORMATO_NO_SOPORTADO, configuracion)

    assert mensaje.texto == "Formato no soportado. Formatos admitidos: .jdx, .csv, .abc"


def prueba_un_solo_formato_admitido(tmp_path: Path) -> None:
    configuracion = _configuracion_con(
        tmp_path, "archivo", "formatos_permitidos", [".jdx"]
    )

    assert mensajes.obtener(mensajes.FORMATO_NO_SOPORTADO, configuracion).texto == (
        "Formato no soportado. Formatos admitidos: .jdx"
    )


@pytest.mark.parametrize(
    ("bytes_maximos", "esperado"),
    [
        (10 * 1024 * 1024, "El tamaño máximo permitido es de 10 MB"),
        (1024 * 1024, "El tamaño máximo permitido es de 1 MB"),
        (1024 * 1024 + 512 * 1024, "El tamaño máximo permitido es de 1.5 MB"),
    ],
)
def prueba_el_tamano_del_mensaje_sale_de_ut03(
    tmp_path: Path, bytes_maximos: int, esperado: str
) -> None:
    configuracion = _configuracion_con(
        tmp_path, "archivo", "tamano_maximo_bytes", bytes_maximos
    )

    assert mensajes.obtener(mensajes.TAMANO_EXCEDIDO, configuracion).texto == esperado


def prueba_el_rango_del_mensaje_sale_de_ut03(tmp_path: Path) -> None:
    configuracion = _configuracion_con(
        tmp_path, "validacion", "rango_requerido_cm1", [1200, 3900]
    )

    assert mensajes.obtener(mensajes.RANGO_INSUFICIENTE, configuracion).texto == (
        "Se requiere cubrir al menos 1200–3900 cm⁻¹"
    )


def prueba_los_puntos_minimos_del_mensaje_salen_de_ut03(tmp_path: Path) -> None:
    configuracion = _configuracion_con(tmp_path, "validacion", "puntos_minimos", 500)

    assert mensajes.obtener(mensajes.PUNTOS_INSUFICIENTES, configuracion).texto == (
        "Mínimo 500 puntos"
    )


# --------------------------------------------------------------------------- #
# RNF-01 · motivo y acción en cada mensaje, sin detalles técnicos
# --------------------------------------------------------------------------- #

CODIGOS_ESPERADOS = (
    mensajes.FORMATO_NO_SOPORTADO,
    mensajes.TAMANO_EXCEDIDO,
    mensajes.RANGO_INSUFICIENTE,
    mensajes.PUNTOS_INSUFICIENTES,
    mensajes.ARCHIVO_NO_ES_TEXTO,
    mensajes.ESTRUCTURA_INVALIDA,
    mensajes.CONFIGURACION_INCOMPLETA,
    mensajes.LECTURA_INTERRUMPIDA,
    # Agregados por T-07 para la capa HTTP (contrato D-5 de la sección 5).
    mensajes.ARCHIVO_NO_RECIBIDO,
    mensajes.ERROR_INTERNO,
    # Agregado por T-08 para la lectura completa de MOD-04.
    mensajes.DATOS_ILEGIBLES,
)


def prueba_el_catalogo_cubre_las_situaciones_del_incremento_1() -> None:
    assert set(mensajes.codigos()) == set(CODIGOS_ESPERADOS)


@pytest.mark.parametrize("codigo", CODIGOS_ESPERADOS)
def prueba_cada_codigo_trae_titulo_texto_y_accion(codigo: str) -> None:
    mensaje = mensajes.obtener(codigo)

    assert mensaje.codigo == codigo
    assert mensaje.titulo.strip()
    assert mensaje.texto.strip()
    assert mensaje.accion.strip()


#: Rastros técnicos que el usuario nunca debe leer (RNF-01).
RASTROS_TECNICOS = (
    "traceback",
    "exception",
    "error 500",
    "none",
    "null",
    ".py",
    "backend/",
    "http",
    "mod-0",
    "ut-0",
    "json",
)


@pytest.mark.parametrize("codigo", CODIGOS_ESPERADOS)
def prueba_ningun_mensaje_muestra_detalles_tecnicos(codigo: str) -> None:
    mensaje = mensajes.obtener(codigo)
    visible = f"{mensaje.titulo} {mensaje.texto} {mensaje.accion}".lower()

    encontrados = [rastro for rastro in RASTROS_TECNICOS if rastro in visible]

    assert not encontrados, f"{codigo} muestra detalles técnicos: {encontrados}"


@pytest.mark.parametrize("codigo", CODIGOS_ESPERADOS)
def prueba_la_accion_le_dice_al_usuario_que_hacer(codigo: str) -> None:
    """La acción es una instrucción, no una descripción del problema."""
    accion = mensajes.obtener(codigo).accion

    assert accion.endswith("."), f"{codigo}: la acción debería ser una oración"
    assert len(accion.split()) >= 3, f"{codigo}: la acción es demasiado corta"


# --------------------------------------------------------------------------- #
# Un código inventado no pasa desapercibido
# --------------------------------------------------------------------------- #


def prueba_un_codigo_que_no_existe_levanta_error() -> None:
    with pytest.raises(mensajes.CodigoDesconocido, match="INVENTADO"):
        mensajes.obtener("INVENTADO")


def prueba_el_mensaje_no_se_puede_modificar() -> None:
    """El catálogo es de solo lectura: nadie reescribe un texto en caliente."""
    mensaje = mensajes.obtener(mensajes.TAMANO_EXCEDIDO)

    with pytest.raises(Exception):
        mensaje.texto = "otro texto"  # type: ignore[misc]
