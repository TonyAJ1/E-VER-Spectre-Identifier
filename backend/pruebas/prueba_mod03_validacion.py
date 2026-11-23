"""Pruebas de T-04 · MOD-03 Validador (contenido real).

Cubren las tres pruebas que el plan del incremento 1 (sección 10) le asigna a
T-04 —**CA-01.3**, **CA-02.4** y **CA-02.5**— y el orden de las cuatro capas de
la tarea: extensión, ¿es texto?, ¿la estructura es la del formato declarado? y
coherencia mínima.

**MOD-03 se prueba aislado, sin MOD-02 real** (sección 9): el contenido entra
como texto, simulado o leído de los fixtures de `datos/pruebas/`. Tal como lo
entrega MOD-02, el texto ya viene sin BOM y con los bytes inválidos convertidos
en el carácter de reemplazo «�» (U+FFFD).

**Lo que todavía no se prueba aquí** es de T-05: contar puntos y mirar el rango.
Por eso dos fixtures que T-05 va a rechazar —el de un punto menos y el de rango
corto— aquí salen **válidos**: su formato es de verdad el que dicen. Hay pruebas
que fijan esa frontera para que nadie la mueva por accidente.

Nada de esto toca la red ni monta la API (es T-07).
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
    CAPA_COHERENCIA,
    CAPA_ESTRUCTURA,
    CAPA_EXTENSION,
    CAPA_TAMANO,
    CAPA_TEXTO,
    Veredicto,
    extension_de,
    revisar_formato,
)
from herramientas.generador_espectros import csv_sintetico, jdx_sintetico

# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #

#: Un `.jdx` mínimo correcto, para ir rompiéndolo de una pieza a la vez.
JDX_VALIDO = (
    "##TITLE=PRUEBA\n"
    "##JCAMP-DX=4.24\n"
    "##XUNITS=1/CM\n"
    "##YUNITS=TRANSMITTANCE\n"
    "##XYDATA=(XY..XY)\n"
    "400.0 0.80\n"
    "500.0 0.75\n"
    "##END=\n"
)

#: Un `.csv` mínimo correcto: pares «número de onda, intensidad».
CSV_VALIDO = "400.0,0.80\n500.0,0.75\n600.0,0.70\n"


def _texto(ruta: Path) -> str:
    """Lee un fixture igual que lo entregaría MOD-02: texto, sin BOM."""
    return ruta.read_bytes().decode("utf-8-sig", errors="replace")


def _con_formatos(*formatos: str) -> Configuracion:
    """La configuración real, con otra lista de formatos permitidos."""
    configuracion = obtener_configuracion()
    return dataclasses.replace(
        configuracion,
        archivo=dataclasses.replace(
            configuracion.archivo, formatos_permitidos=tuple(formatos)
        ),
    )


def _con_etiquetas(*etiquetas: str) -> Configuracion:
    """La configuración real, con otras etiquetas obligatorias de JCAMP-DX."""
    configuracion = obtener_configuracion()
    return dataclasses.replace(
        configuracion,
        validacion=dataclasses.replace(
            configuracion.validacion, jcamp_etiquetas_obligatorias=tuple(etiquetas)
        ),
    )


# --------------------------------------------------------------------------- #
# CA-01.3 · formato no admitido → mensaje de formato de UT-02
# --------------------------------------------------------------------------- #


def prueba_ca_01_3_rechaza_el_png_con_el_mensaje_de_formato(
    carpeta_fixtures: Path,
) -> None:
    veredicto = revisar_formato("imagen.png", _texto(carpeta_fixtures / "imagen.png"))

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.FORMATO_NO_SOPORTADO
    assert veredicto.capa == CAPA_EXTENSION, (
        "la capa de extensión va primero: si el PNG llegara a la capa de texto, "
        "el usuario vería «no es texto» en vez del mensaje de formato"
    )


def prueba_ca_01_3_el_mensaje_nombra_los_formatos_de_ut03(
    carpeta_fixtures: Path,
) -> None:
    veredicto = revisar_formato("imagen.png", _texto(carpeta_fixtures / "imagen.png"))
    mensaje = mensajes.obtener(veredicto.codigo)

    for formato in obtener_configuracion().archivo.formatos_permitidos:
        assert formato in mensaje.texto
    assert mensaje.accion.strip()


@pytest.mark.parametrize(
    "nombre",
    ["espectro.txt", "espectro.dx", "espectro.xlsx", "espectro", "espectro.", ".csv"],
)
def prueba_ca_01_3_solo_pasan_las_extensiones_de_ut03(nombre: str) -> None:
    """`.dx` queda fuera a propósito (D-0), igual que cualquier otra."""
    veredicto = revisar_formato(nombre, CSV_VALIDO)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.FORMATO_NO_SOPORTADO


def prueba_la_extension_no_distingue_mayusculas() -> None:
    assert revisar_formato("ESPECTRO.CSV", CSV_VALIDO).valido
    assert revisar_formato("Espectro.Jdx", JDX_VALIDO).valido


def prueba_el_archivo_sin_nombre_se_rechaza_por_formato() -> None:
    """Así llega de MOD-02 una subida sin nombre."""
    veredicto = revisar_formato("(sin nombre)", CSV_VALIDO)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.FORMATO_NO_SOPORTADO


# --------------------------------------------------------------------------- #
# CA-02.5 · binario disfrazado de .csv → rechazo por su contenido
# --------------------------------------------------------------------------- #


def prueba_ca_02_5_rechaza_el_binario_disfrazado_por_su_contenido(
    carpeta_fixtures: Path,
) -> None:
    contenido = _texto(carpeta_fixtures / "binario-disfrazado.csv")

    veredicto = revisar_formato("ejecutable.csv", contenido)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ARCHIVO_NO_ES_TEXTO
    assert veredicto.capa == CAPA_TEXTO, (
        "la extensión decía .csv y se le creyó; lo que lo delata es el contenido"
    )


@pytest.mark.parametrize(
    ("caso", "contenido"),
    [
        ("byte nulo", "400.0,0.80\n\x00\x00\n"),
        ("carácter de escape", "400.0,0.80\n\x1b[31m\n"),
        ("byte de borrado", "400.0,0.80\n\x7f\n"),
        ("byte inválido marcado por MOD-02", "400.0,0.80\n�\n"),
    ],
)
def prueba_ca_02_5_lo_que_no_es_texto_se_rechaza(caso: str, contenido: str) -> None:
    """Defensa de RNF-03: nunca se interpreta algo que no sea texto."""
    veredicto = revisar_formato("espectro.csv", contenido)

    assert not veredicto.valido, caso
    assert veredicto.codigo == mensajes.ARCHIVO_NO_ES_TEXTO, caso


def prueba_los_espacios_normales_del_texto_si_se_aceptan() -> None:
    """Tabulador, salto de línea y retorno de carro son texto corriente."""
    veredicto = revisar_formato("espectro.csv", "400.0,0.80\r\n500.0,0.75\r\n")

    assert veredicto.valido


# --------------------------------------------------------------------------- #
# CA-02.4 · archivo vacío y .jdx truncado → motivo, sin excepción
# --------------------------------------------------------------------------- #


def prueba_ca_02_4_el_archivo_vacio_da_su_motivo(carpeta_fixtures: Path) -> None:
    veredicto = revisar_formato(
        "archivo-vacio.csv", _texto(carpeta_fixtures / "archivo-vacio.csv")
    )

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA
    assert veredicto.capa == CAPA_ESTRUCTURA


def prueba_ca_02_4_el_jdx_truncado_da_su_motivo(carpeta_fixtures: Path) -> None:
    """Al fixture le falta `##END=`: el archivo se cortó a la mitad."""
    veredicto = revisar_formato(
        "espectro-truncado.jdx", _texto(carpeta_fixtures / "espectro-truncado.jdx")
    )

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA
    assert veredicto.capa == CAPA_ESTRUCTURA


def prueba_ca_02_4_el_rechazo_trae_motivo_y_accion_sin_detalles_tecnicos(
    carpeta_fixtures: Path,
) -> None:
    veredicto = revisar_formato(
        "espectro-truncado.jdx", _texto(carpeta_fixtures / "espectro-truncado.jdx")
    )
    mensaje = mensajes.obtener(veredicto.codigo)

    assert mensaje.titulo.strip()
    assert mensaje.texto.strip()
    assert mensaje.accion.strip()
    for tecnico in ("##END=", "Traceback", "ValueError", "backend"):
        assert tecnico not in mensaje.texto
        assert tecnico not in mensaje.accion


ARCHIVOS_HOSTILES = (
    "",
    "\x00",
    "�" * 10,
    "no soy un espectro",
    ",",
    ",,,\n,,,\n",
    "400.0\n",
    "##TITLE=\n",
    "##END=\n",
    "\n\n\n",
    "   \t  \n",
    "400.0,0.8" + "0" * 5000,
    "e" * 10000,
    "400.0,0.80\n" + "\n" * 500,
)


@pytest.mark.parametrize("contenido", ARCHIVOS_HOSTILES)
@pytest.mark.parametrize("nombre", ["espectro.csv", "espectro.jdx", "espectro.png"])
def prueba_ca_02_4_ningun_archivo_hace_estallar_al_validador(
    nombre: str, contenido: str
) -> None:
    """«No se detiene de forma abrupta»: siempre sale un veredicto, nunca una
    excepción."""
    veredicto = revisar_formato(nombre, contenido)

    assert isinstance(veredicto, Veredicto)
    if not veredicto.valido:
        assert veredicto.codigo in mensajes.codigos()


def prueba_ca_02_4_despues_de_un_rechazo_el_siguiente_archivo_se_atiende(
    carpeta_fixtures: Path,
) -> None:
    """«Atiende la siguiente petición»: MOD-03 no guarda estado entre llamadas."""
    primero = revisar_formato(
        "archivo-vacio.csv", _texto(carpeta_fixtures / "archivo-vacio.csv")
    )
    segundo = revisar_formato(
        "espectro-valido.jdx", _texto(carpeta_fixtures / "espectro-valido.jdx")
    )
    tercero = revisar_formato(
        "binario-disfrazado.csv", _texto(carpeta_fixtures / "binario-disfrazado.csv")
    )
    cuarto = revisar_formato(
        "espectro-valido-900-puntos.csv",
        _texto(carpeta_fixtures / "espectro-valido-900-puntos.csv"),
    )

    assert not primero.valido
    assert segundo.valido
    assert not tercero.valido
    assert cuarto.valido


# --------------------------------------------------------------------------- #
# Los fixtures válidos pasan
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "archivo",
    [
        "espectro-valido.jdx",
        "espectro-valido-900-puntos.csv",
        "espectro-puntos-minimos.csv",
    ],
)
def prueba_los_fixtures_validos_pasan_las_cuatro_capas(
    carpeta_fixtures: Path, archivo: str
) -> None:
    veredicto = revisar_formato(archivo, _texto(carpeta_fixtures / archivo))

    assert veredicto.valido, veredicto.detalle
    assert veredicto.codigo is None
    assert veredicto.extension == ("." + archivo.rsplit(".", 1)[-1])


# --------------------------------------------------------------------------- #
# La frontera con T-05: aquí no se cuentan puntos ni se mira el rango
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "archivo", ["espectro-un-punto-menos.csv", "espectro-rango-corto.csv"]
)
def prueba_lo_que_le_toca_a_t05_todavia_pasa(
    carpeta_fixtures: Path, archivo: str
) -> None:
    """Pocos puntos o rango corto **no** son problema de formato.

    Estos dos archivos son de verdad `.csv` de pares numéricos: T-04 los acepta
    y T-05 los rechaza con «mínimo … puntos» y «se requiere cubrir al menos …».
    Si algún día esta prueba falla, alguien metió T-05 dentro de T-04.
    """
    veredicto = revisar_formato(archivo, _texto(carpeta_fixtures / archivo))

    assert veredicto.valido, veredicto.detalle


def prueba_t04_no_rechaza_por_cantidad_de_puntos() -> None:
    """Dos pares bastan para T-04; el mínimo de UT-03 lo aplica T-05."""
    veredicto = revisar_formato("espectro.csv", "400.0,0.80\n4000.0,0.75\n")

    assert veredicto.valido


# --------------------------------------------------------------------------- #
# Capa 2 · la estructura tiene que ser la del formato declarado
# --------------------------------------------------------------------------- #


def prueba_un_jdx_con_nombre_de_csv_se_rechaza() -> None:
    """Extensión mentirosa (sección 9): el contenido no parsea como CSV."""
    veredicto = revisar_formato("espectro.csv", JDX_VALIDO)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA
    assert veredicto.capa == CAPA_ESTRUCTURA


def prueba_un_csv_con_nombre_de_jdx_se_rechaza() -> None:
    veredicto = revisar_formato("espectro.jdx", CSV_VALIDO)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA


@pytest.mark.parametrize(
    ("caso", "contenido"),
    [
        (
            "sin ##TITLE= en la primera línea",
            JDX_VALIDO.replace("##TITLE=PRUEBA\n", "$$ comentario\n##TITLE=PRUEBA\n"),
        ),
        ("sin ##END= al final", JDX_VALIDO.replace("##END=\n", "")),
        (
            "##END= que no es la última línea",
            JDX_VALIDO.replace("##END=\n", "##END=\n400.0 0.80\n"),
        ),
        ("sin ##JCAMP-DX=", JDX_VALIDO.replace("##JCAMP-DX=4.24\n", "")),
        ("sin ##XUNITS=", JDX_VALIDO.replace("##XUNITS=1/CM\n", "")),
        ("sin ##YUNITS=", JDX_VALIDO.replace("##YUNITS=TRANSMITTANCE\n", "")),
        ("sin etiqueta de datos", JDX_VALIDO.replace("##XYDATA=(XY..XY)\n", "")),
    ],
)
def prueba_al_jdx_le_falta_una_pieza_y_se_rechaza(caso: str, contenido: str) -> None:
    veredicto = revisar_formato("espectro.jdx", contenido)

    assert not veredicto.valido, caso
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA, caso


def prueba_el_jdx_acepta_tambien_la_tabla_de_picos() -> None:
    """UT-03 admite `##XYDATA=` o `##PEAK TABLE=`: basta una de las dos."""
    contenido = JDX_VALIDO.replace("##XYDATA=(XY..XY)", "##PEAK TABLE=(XY..XY)")

    assert revisar_formato("espectro.jdx", contenido).valido


def prueba_el_jdx_tolera_lineas_en_blanco_al_final() -> None:
    """Un editor de texto agrega saltos al final; eso no es un archivo truncado."""
    assert revisar_formato("espectro.jdx", JDX_VALIDO + "\n\n").valido


def prueba_las_etiquetas_obligatorias_salen_de_ut03() -> None:
    """Si UT-03 pide una etiqueta más, el mismo archivo deja de pasar."""
    configuracion = _con_etiquetas(
        "##TITLE=", "##JCAMP-DX=", "##XUNITS=", "##YUNITS=", "##END=", "##NPOINTS="
    )

    assert revisar_formato("espectro.jdx", JDX_VALIDO).valido
    assert not revisar_formato("espectro.jdx", JDX_VALIDO, configuracion=configuracion).valido


def prueba_los_formatos_permitidos_salen_de_ut03() -> None:
    """Si UT-03 cambia la lista, cambia qué extensiones pasan, sin tocar código."""
    configuracion = _con_formatos(".jdx")

    assert revisar_formato("espectro.jdx", JDX_VALIDO, configuracion=configuracion).valido
    rechazado = revisar_formato("espectro.csv", CSV_VALIDO, configuracion=configuracion)
    assert not rechazado.valido
    assert rechazado.codigo == mensajes.FORMATO_NO_SOPORTADO


def prueba_un_formato_permitido_que_mod_03_no_sabe_revisar_se_rechaza() -> None:
    """Falla cerrado, no abierto.

    Si alguien agrega una extensión a UT-03 —`.dx`, por ejemplo, que D-0 dejó
    fuera del incremento— MOD-03 todavía no sabe qué estructura esperar de ella.
    Dejarla pasar sin revisar sería peor que rechazarla: enseñarle el formato
    nuevo es una línea, y hasta que alguien la escriba el archivo no entra.
    """
    configuracion = _con_formatos(".txt")

    veredicto = revisar_formato("espectro.txt", CSV_VALIDO, configuracion=configuracion)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA
    assert veredicto.capa == CAPA_ESTRUCTURA


@pytest.mark.parametrize(
    ("caso", "contenido"),
    [
        ("texto en vez de números", "400.0,0.80\nonda,intensidad\n"),
        ("encabezado y nada más", "onda,intensidad\n"),
        ("dos encabezados", "onda,intensidad\ncm-1,T\n400.0,0.80\n"),
        ("una sola columna", "400.0\n500.0\n600.0\n"),
        ("tres columnas", "400.0,0.80,extra\n500.0,0.75,extra\n"),
        ("punto y coma con tres campos", "400,0;0,80;1\n500,0;0,75;1\n"),
        ("separadores mezclados", "400.0;0.80\n500.0,0.75\n"),
        ("columna vacía", "400.0,\n500.0,\n"),
        ("solo comas", ",\n,\n"),
    ],
)
def prueba_al_csv_no_le_salen_los_pares_y_se_rechaza(caso: str, contenido: str) -> None:
    veredicto = revisar_formato("espectro.csv", contenido)

    assert not veredicto.valido, caso
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA, caso


# --- Requerimientos §6.1: separador coma o punto y coma, encabezado opcional --- #


@pytest.mark.parametrize(
    ("caso", "contenido"),
    [
        ("separado con punto y coma", "400.0;0.80\n500.0;0.75\n"),
        ("punto y coma con coma decimal (Excel en español)", "400,0;0,805\n500,0;0,750\n"),
        ("encabezado con coma", "onda,intensidad\n400.0,0.80\n500.0,0.75\n"),
        ("encabezado con punto y coma", "Numero de onda (cm-1);T\n400,0;0,80\n500,0;0,75\n"),
        ("encabezado tras líneas en blanco", "\n\nonda,intensidad\n400.0,0.80\n500.0,0.75\n"),
    ],
)
def prueba_el_csv_admite_lo_que_pide_la_seccion_6_1(caso: str, contenido: str) -> None:
    """Rechazar un encabezado válido o el `;` sería incumplir Requerimientos §6.1."""
    veredicto = revisar_formato("espectro.csv", contenido)

    assert veredicto.valido, f"{caso}: {veredicto.detalle}"


def prueba_el_encabezado_no_cuenta_como_fila_de_datos() -> None:
    """Encabezado más un solo par sigue siendo un espectro de un punto."""
    veredicto = revisar_formato("espectro.csv", "onda,intensidad\n400.0,0.80\n")

    assert not veredicto.valido
    assert veredicto.capa == CAPA_COHERENCIA


def prueba_con_punto_y_coma_la_coma_es_decimal() -> None:
    """`-400,0;0,80` es un número de onda negativo, no un campo de más."""
    veredicto = revisar_formato("espectro.csv", "-400,0;0,80\n500,0;0,75\n")

    assert not veredicto.valido
    assert veredicto.capa == CAPA_COHERENCIA


def prueba_el_csv_tolera_espacios_alrededor_de_los_numeros() -> None:
    assert revisar_formato("espectro.csv", " 400.0 , 0.80 \n 500.0 , 0.75 \n").valido


def prueba_el_csv_tolera_lineas_en_blanco_entre_filas() -> None:
    assert revisar_formato("espectro.csv", "400.0,0.80\n\n500.0,0.75\n\n").valido


def prueba_el_csv_acepta_notacion_cientifica() -> None:
    """Varios programas exportan así; sigue siendo un número."""
    assert revisar_formato("espectro.csv", "4.0e2,8.0e-1\n5.0e2,7.5e-1\n").valido


def prueba_el_csv_con_coma_decimal_pasa_t04_y_lo_atrapa_t05() -> None:
    """Límite conocido, anotado a propósito (SUPUESTO para el equipo).

    Excel en español exporta «400,0» con coma decimal. Esa línea trae dos
    campos numéricos, así que es indistinguible de un par de enteros: MOD-03 no
    puede rechazarla por estructura sin inventar una regla. Pasa T-04 y la
    atrapa T-05, porque los números de onda que salen (400, 500…) no cubren el
    rango requerido. Si el equipo quiere un rechazo temprano y con su propio
    mensaje, es una decisión de alcance, no algo que yo deba meter aquí.
    """
    veredicto = revisar_formato("espectro.csv", "400,0\n500,0\n600,0\n")

    assert veredicto.valido


# --------------------------------------------------------------------------- #
# Capa 3 · coherencia mínima
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("caso", "contenido"),
    [
        ("número de onda cero", "0.0,0.80\n500.0,0.75\n"),
        ("número de onda negativo", "-400.0,0.80\n-500.0,0.75\n"),
        ("número de onda infinito", "inf,0.80\n500.0,0.75\n"),
        ("intensidad que no es número", "400.0,nan\n500.0,0.75\n"),
    ],
)
def prueba_los_valores_implausibles_se_rechazan(caso: str, contenido: str) -> None:
    veredicto = revisar_formato("espectro.csv", contenido)

    assert not veredicto.valido, caso
    assert veredicto.codigo == mensajes.ESTRUCTURA_INVALIDA, caso
    assert veredicto.capa == CAPA_COHERENCIA, caso


def prueba_un_csv_de_una_sola_fila_no_es_un_espectro() -> None:
    """Dos puntos es el piso de lo que puede llamarse espectro.

    No es el mínimo de UT-03 —eso es T-05—, es que con un punto no hay curva.
    """
    veredicto = revisar_formato("espectro.csv", "400.0,0.80\n")

    assert not veredicto.valido
    assert veredicto.capa == CAPA_COHERENCIA


def prueba_un_jdx_sin_una_sola_linea_de_datos_se_rechaza() -> None:
    contenido = (
        "##TITLE=PRUEBA\n"
        "##JCAMP-DX=4.24\n"
        "##XUNITS=1/CM\n"
        "##YUNITS=TRANSMITTANCE\n"
        "##XYDATA=(XY..XY)\n"
        "##END=\n"
    )

    veredicto = revisar_formato("espectro.jdx", contenido)

    assert not veredicto.valido
    assert veredicto.capa == CAPA_COHERENCIA


def prueba_un_jdx_con_numero_de_onda_negativo_se_rechaza() -> None:
    contenido = JDX_VALIDO.replace("400.0 0.80\n", "-400.0 0.80\n")

    veredicto = revisar_formato("espectro.jdx", contenido)

    assert not veredicto.valido
    assert veredicto.capa == CAPA_COHERENCIA


def prueba_el_jdx_no_se_interpreta_mas_alla_de_lo_necesario() -> None:
    """Las formas comprimidas de JCAMP-DX son trabajo de MOD-04 (incremento 2).

    T-04 solo comprueba que haya datos y que el primer número de onda sea
    plausible; un bloque comprimido no se descifra aquí, así que no se rechaza
    por no entenderlo.
    """
    contenido = JDX_VALIDO.replace(
        "400.0 0.80\n500.0 0.75\n", "400.0 J80K75j12%%\n"
    )

    assert revisar_formato("espectro.jdx", contenido).valido


# --------------------------------------------------------------------------- #
# El orden de las capas
# --------------------------------------------------------------------------- #


def prueba_el_formato_se_revisa_antes_que_el_contenido(
    carpeta_fixtures: Path,
) -> None:
    """Un PNG es binario **y** de formato no admitido: manda el formato."""
    contenido = _texto(carpeta_fixtures / "imagen.png")

    como_png = revisar_formato("imagen.png", contenido)
    como_csv = revisar_formato("imagen.csv", contenido)

    assert como_png.codigo == mensajes.FORMATO_NO_SOPORTADO
    assert como_csv.codigo == mensajes.ARCHIVO_NO_ES_TEXTO, (
        "con una extensión admitida, lo que delata al PNG es su contenido"
    )


def prueba_el_texto_se_revisa_antes_que_la_estructura() -> None:
    """Un binario tampoco tiene estructura, pero el motivo honesto es el otro."""
    veredicto = revisar_formato("espectro.jdx", "\x00\x00\x00")

    assert veredicto.codigo == mensajes.ARCHIVO_NO_ES_TEXTO


def prueba_la_estructura_se_revisa_antes_que_la_coherencia() -> None:
    veredicto = revisar_formato("espectro.csv", "-400.0,0.80\nsin pares\n")

    assert veredicto.capa == CAPA_ESTRUCTURA


# --------------------------------------------------------------------------- #
# El indicador de «tamaño correcto» del contrato de la sección 5
# --------------------------------------------------------------------------- #


def prueba_no_se_valida_contenido_cuyo_tamano_no_se_confirmo() -> None:
    """Red de seguridad: si MOD-02 no confirmó el tamaño, MOD-03 no sigue.

    No debería pasar —la API solo llama a MOD-03 cuando MOD-02 aceptó—, pero si
    alguien conecta mal los módulos, el indicador del contrato sirve de freno en
    vez de ser un campo decorativo.
    """
    veredicto = revisar_formato("espectro.csv", CSV_VALIDO, tamano_correcto=False)

    assert not veredicto.valido
    assert veredicto.codigo == mensajes.TAMANO_EXCEDIDO
    assert veredicto.capa == CAPA_TAMANO


# --------------------------------------------------------------------------- #
# El veredicto y sus piezas
# --------------------------------------------------------------------------- #


def prueba_el_veredicto_valido_no_trae_codigo_ni_capa() -> None:
    veredicto = revisar_formato("espectro.csv", CSV_VALIDO)

    assert veredicto.valido
    assert veredicto.codigo is None
    assert veredicto.capa is None
    assert veredicto.nombre == "espectro.csv"
    assert veredicto.extension == ".csv"


def prueba_todo_rechazo_se_puede_traducir_con_ut02() -> None:
    """Cada código que sale de MOD-03 tiene mensaje con motivo y acción."""
    casos = ["imagen.png", "espectro.csv", "espectro.jdx"]
    contenidos = ["\x00", "", "no soy un espectro"]

    for nombre in casos:
        for contenido in contenidos:
            veredicto = revisar_formato(nombre, contenido)
            assert not veredicto.valido
            mensaje = mensajes.obtener(veredicto.codigo)
            assert mensaje.texto.strip()
            assert mensaje.accion.strip()


def prueba_el_veredicto_no_se_puede_modificar() -> None:
    veredicto = revisar_formato("espectro.csv", CSV_VALIDO)

    with pytest.raises(dataclasses.FrozenInstanceError):
        veredicto.valido = False  # type: ignore[misc]


def prueba_el_detalle_es_para_el_registro_no_para_el_usuario() -> None:
    """El detalle explica al equipo qué capa falló; el usuario ve UT-02."""
    veredicto = revisar_formato("espectro.jdx", CSV_VALIDO)

    assert veredicto.detalle.strip(), "un rechazo debe decir al equipo por qué"


@pytest.mark.parametrize(
    ("nombre", "esperada"),
    [
        ("acetona.jdx", ".jdx"),
        ("acetona.JDX", ".jdx"),
        ("acetona.espectro.csv", ".csv"),
        ("acetona", None),
        ("acetona.", None),
        (".csv", None),
        ("(sin nombre)", None),
    ],
)
def prueba_extension_de(nombre: str, esperada: str | None) -> None:
    assert extension_de(nombre) == esperada


# --------------------------------------------------------------------------- #
# Registros
# --------------------------------------------------------------------------- #


def prueba_los_registros_no_guardan_el_contenido_del_espectro(
    caplog: pytest.LogCaptureFixture,
) -> None:
    contenido = "400.0,0.512345\n500.0,0.698765\n"

    with caplog.at_level(logging.INFO):
        veredicto = revisar_formato("acetona.csv", contenido)

    registrado = "\n".join(r.getMessage() for r in caplog.records)

    assert veredicto.valido
    assert caplog.records, "MOD-03 debe registrar el veredicto"
    assert "acetona.csv" in registrado
    assert "0.512345" not in registrado, "el contenido nunca va al registro (RNF-09)"
    assert "400.0" not in registrado


def prueba_el_registro_del_rechazo_dice_el_codigo(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        veredicto = revisar_formato("imagen.png", "cualquier cosa")

    registrado = "\n".join(r.getMessage() for r in caplog.records)

    assert not veredicto.valido
    assert mensajes.FORMATO_NO_SOPORTADO in registrado
    assert "imagen.png" in registrado


# --------------------------------------------------------------------------- #
# Archivos grandes: el validador no se cae con los pesados
# --------------------------------------------------------------------------- #


def prueba_un_csv_del_tamano_maximo_se_valida_sin_problema(
    csv_tamano_maximo: Path,
) -> None:
    """El archivo de CA-01.2, ahora visto por MOD-03."""
    veredicto = revisar_formato("espectro-maximo.csv", _texto(csv_tamano_maximo))

    assert veredicto.valido, veredicto.detalle


def prueba_un_jdx_grande_se_valida_sin_problema() -> None:
    contenido = jdx_sintetico("GRANDE", 20000, 400.0, 4000.0).decode("ascii")

    assert revisar_formato("grande.jdx", contenido).valido


def prueba_un_csv_grande_se_valida_sin_problema() -> None:
    contenido = csv_sintetico(20000, 400.0, 4000.0).decode("ascii")

    assert revisar_formato("grande.csv", contenido).valido
