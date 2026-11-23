"""Pruebas de T-01 · UT-03 Configuración.

Cubren la prueba «UT-03 · configuración incompleta» de la sección 10 del plan del
incremento 1 y la condición de «terminado» de T-01:

- el archivo del repositorio es el que el código carga de verdad (D-6);
- los parámetros de la sección 3 llegan con el valor que dice el plan;
- si falta una llave obligatoria o un valor es incoherente, el backend
  **no arranca en silencio**;
- el bloque `motor` no es obligatorio todavía (incremento 3);
- cambiar un valor del archivo cambia el comportamiento, sin tocar código;
- ningún otro módulo repite los valores (regla 1 de CLAUDE.md).
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest

from backend.utilerias.configuracion import (
    NOMBRE_ARCHIVO,
    PATRON_ARCHIVO,
    RUTA_PARAMETROS,
    ErrorDeConfiguracion,
    cargar,
    obtener,
    recargar,
)

RAIZ = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #


def _datos_del_repositorio() -> dict[str, Any]:
    """El contenido del archivo real, para derivar de él los casos de error."""
    return json.loads(RUTA_PARAMETROS.read_text(encoding="utf-8"))


def _escribir(carpeta: Path, datos: Any) -> Path:
    ruta = carpeta / NOMBRE_ARCHIVO
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


# --------------------------------------------------------------------------- #
# D-6 · el archivo del repositorio es el que se carga
# --------------------------------------------------------------------------- #


def prueba_el_archivo_que_carga_el_codigo_es_el_del_repositorio() -> None:
    assert RUTA_PARAMETROS.is_file(), f"no existe {RUTA_PARAMETROS}"
    assert RUTA_PARAMETROS.parent == RAIZ / "backend" / "utilerias" / "configuracion"
    assert RUTA_PARAMETROS.name == NOMBRE_ARCHIVO
    assert cargar().ruta == RUTA_PARAMETROS


def prueba_el_archivo_no_es_una_plantilla() -> None:
    """D-6: el archivo de parámetros no lleva sufijo `.ejemplo`, porque no es una
    plantilla para copiar: es la fuente operativa y va versionado."""
    assert ".ejemplo" not in NOMBRE_ARCHIVO, (
        "D-6 quitó el sufijo «.ejemplo»: este archivo es la fuente, no una "
        "plantilla"
    )


def prueba_solo_hay_un_archivo_de_parametros() -> None:
    """D-6: si algún día aparece un segundo `parametros*.json`, uno de los dos
    deja de ser la fuente y la decisión hay que volverla a tomar."""
    candidatos = sorted(p.name for p in RUTA_PARAMETROS.parent.glob(PATRON_ARCHIVO))

    assert candidatos == [NOMBRE_ARCHIVO], (
        f"UT-03 debería tener un solo archivo de parámetros; hay: {candidatos}"
    )


# --------------------------------------------------------------------------- #
# Sección 3 · los parámetros confirmados
# --------------------------------------------------------------------------- #


def prueba_los_parametros_confirmados_de_la_seccion_3() -> None:
    configuracion = cargar()

    assert configuracion.archivo.tamano_maximo_bytes == 5_242_880  # 5 MB
    assert configuracion.archivo.formatos_permitidos == (".jdx", ".csv")

    assert configuracion.validacion.puntos_minimos == 300
    assert configuracion.validacion.rango_requerido_cm1 == (1400.0, 3700.0)
    assert configuracion.validacion.jcamp_etiquetas_obligatorias == (
        "##TITLE=",
        "##JCAMP-DX=",
        "##XUNITS=",
        "##YUNITS=",
        "##END=",
    )
    assert configuracion.validacion.jcamp_etiquetas_datos_una_de == (
        "##XYDATA=",
        "##PEAK TABLE=",
    )


def prueba_el_bloque_motor_no_es_obligatorio_en_este_incremento(tmp_path: Path) -> None:
    """El umbral y los pesos de fusión son del incremento 3: hoy no deben
    impedir que el backend levante."""
    datos = _datos_del_repositorio()
    datos.pop("motor", None)

    configuracion = cargar(_escribir(tmp_path, datos))

    assert configuracion.validacion.puntos_minimos == 300


# --------------------------------------------------------------------------- #
# UT-03 · configuración incompleta (sección 10)
# --------------------------------------------------------------------------- #

LLAVES_OBLIGATORIAS = [
    ("archivo", "tamano_maximo_bytes"),
    ("archivo", "formatos_permitidos"),
    ("validacion", "puntos_minimos"),
    ("validacion", "rango_requerido_cm1"),
    ("validacion", "jcamp_etiquetas_obligatorias"),
    ("validacion", "jcamp_etiquetas_datos_una_de"),
    ("procesamiento", "puntos_rejilla"),
    ("procesamiento", "rango_rejilla_cm1"),
]


@pytest.mark.parametrize(("bloque", "llave"), LLAVES_OBLIGATORIAS)
def prueba_falta_una_llave_obligatoria_y_no_arranca(
    tmp_path: Path, bloque: str, llave: str
) -> None:
    datos = _datos_del_repositorio()
    del datos[bloque][llave]

    with pytest.raises(ErrorDeConfiguracion) as fallo:
        cargar(_escribir(tmp_path, datos))

    mensaje = str(fallo.value)
    assert f"{bloque}.{llave}" in mensaje, mensaje
    assert "UT-03" in mensaje
    # El error dice qué hacer, no solo qué pasó.
    assert "Corrija" in mensaje


@pytest.mark.parametrize("bloque", ["archivo", "validacion", "procesamiento"])
def prueba_falta_un_bloque_completo_y_no_arranca(tmp_path: Path, bloque: str) -> None:
    datos = _datos_del_repositorio()
    del datos[bloque]

    with pytest.raises(ErrorDeConfiguracion, match=bloque):
        cargar(_escribir(tmp_path, datos))


def _con(bloque: str, llave: str, valor: Any) -> dict[str, Any]:
    datos = _datos_del_repositorio()
    datos[bloque][llave] = valor
    return datos


CASOS_INCOHERENTES = [
    ("tamaño máximo en cero", _con("archivo", "tamano_maximo_bytes", 0)),
    ("tamaño máximo negativo", _con("archivo", "tamano_maximo_bytes", -1)),
    ("tamaño máximo como texto", _con("archivo", "tamano_maximo_bytes", "5242880")),
    ("tamaño máximo booleano", _con("archivo", "tamano_maximo_bytes", True)),
    ("formatos vacíos", _con("archivo", "formatos_permitidos", [])),
    ("formato sin punto", _con("archivo", "formatos_permitidos", ["jdx"])),
    ("formato repetido", _con("archivo", "formatos_permitidos", [".jdx", ".jdx"])),
    ("formatos como texto", _con("archivo", "formatos_permitidos", ".jdx")),
    ("puntos mínimos en cero", _con("validacion", "puntos_minimos", 0)),
    ("puntos mínimos decimales", _con("validacion", "puntos_minimos", 300.5)),
    ("rango invertido", _con("validacion", "rango_requerido_cm1", [3700, 1400])),
    ("rango de un solo valor", _con("validacion", "rango_requerido_cm1", [1400])),
    ("rango de tres valores", _con("validacion", "rango_requerido_cm1", [1, 2, 3])),
    ("rango negativo", _con("validacion", "rango_requerido_cm1", [-1400, 3700])),
    ("rango de textos", _con("validacion", "rango_requerido_cm1", ["1400", "3700"])),
    ("etiquetas vacías", _con("validacion", "jcamp_etiquetas_obligatorias", [])),
    (
        "etiqueta en blanco",
        _con("validacion", "jcamp_etiquetas_obligatorias", ["##TITLE=", "  "]),
    ),
    ("etiquetas de datos vacías", _con("validacion", "jcamp_etiquetas_datos_una_de", [])),
    ("rejilla de un solo punto", _con("procesamiento", "puntos_rejilla", 1)),
    ("rejilla decimal", _con("procesamiento", "puntos_rejilla", 1024.5)),
    ("rejilla invertida", _con("procesamiento", "rango_rejilla_cm1", [4000, 400])),
]


@pytest.mark.parametrize(
    "datos", [caso[1] for caso in CASOS_INCOHERENTES], ids=[c[0] for c in CASOS_INCOHERENTES]
)
def prueba_un_valor_incoherente_y_no_arranca(
    tmp_path: Path, datos: dict[str, Any]
) -> None:
    with pytest.raises(ErrorDeConfiguracion):
        cargar(_escribir(tmp_path, copy.deepcopy(datos)))


def prueba_el_archivo_no_existe(tmp_path: Path) -> None:
    with pytest.raises(ErrorDeConfiguracion, match="no se encontró"):
        cargar(tmp_path / "no-esta.json")


def prueba_el_archivo_no_es_json_valido(tmp_path: Path) -> None:
    ruta = tmp_path / NOMBRE_ARCHIVO
    ruta.write_text('{"archivo": {', encoding="utf-8")

    with pytest.raises(ErrorDeConfiguracion, match="JSON"):
        cargar(ruta)


def prueba_el_json_no_es_un_objeto(tmp_path: Path) -> None:
    with pytest.raises(ErrorDeConfiguracion, match="objeto JSON"):
        cargar(_escribir(tmp_path, [1, 2, 3]))


# --------------------------------------------------------------------------- #
# T-01 · «prueba de que sirve de verdad»
# --------------------------------------------------------------------------- #


def prueba_cambiar_un_valor_del_archivo_cambia_el_parametro(tmp_path: Path) -> None:
    """Condición de «terminado» de T-01: cambiar `puntos_minimos` a 500 en el
    archivo cambia el valor que leen los módulos, sin tocar una línea de código.

    La otra mitad —que el veredicto de MOD-03 cambie con él— se verifica en T-05,
    cuando MOD-03 exista.
    """
    datos = _datos_del_repositorio()
    datos["validacion"]["puntos_minimos"] = 500

    modificada = cargar(_escribir(tmp_path, datos))

    assert modificada.validacion.puntos_minimos == 500
    # El archivo del repositorio queda intacto.
    assert cargar().validacion.puntos_minimos == 300


def prueba_obtener_guarda_en_memoria_y_recargar_la_reemplaza(tmp_path: Path) -> None:
    original = obtener()
    assert obtener() is original, "obtener() debería devolver siempre la misma"

    datos = _datos_del_repositorio()
    datos["validacion"]["puntos_minimos"] = 500
    recargar(_escribir(tmp_path, datos))
    try:
        assert obtener().validacion.puntos_minimos == 500
    finally:
        recargar()  # deja la configuración del repositorio para las demás pruebas

    assert obtener().validacion.puntos_minimos == 300


# --------------------------------------------------------------------------- #
# Regla 1 de CLAUDE.md · nada «hardcodeado»
# --------------------------------------------------------------------------- #

#: Valores que solo pueden vivir en UT-03. No se incluyen `.jdx` ni `.csv`:
#: esas cadenas sí aparecerán en el código de MOD-03 para decidir **qué**
#: validador estructural aplica (una bifurcación, no un parámetro).
VALORES_PROHIBIDOS = [
    r"5_?242_?880",
    r"\b1400\b",
    r"\b3700\b",
    r"\b300\b",
]


def prueba_ningun_modulo_repite_los_valores_de_ut03() -> None:
    exentas = {
        RAIZ / "backend" / "pruebas",
        RAIZ / "backend" / "utilerias" / "configuracion",
    }
    hallazgos: list[str] = []

    for archivo in sorted((RAIZ / "backend").rglob("*.py")):
        if any(carpeta in archivo.parents for carpeta in exentas):
            continue
        texto = archivo.read_text(encoding="utf-8")
        for numero, linea in enumerate(texto.splitlines(), start=1):
            if any(re.search(patron, linea) for patron in VALORES_PROHIBIDOS):
                relativa = archivo.relative_to(RAIZ).as_posix()
                hallazgos.append(f"{relativa}:{numero}: {linea.strip()}")

    assert not hallazgos, (
        "estos valores deben leerse de UT-03, no escribirse en el código:\n"
        + "\n".join(hallazgos)
    )
