"""UT-03 · Configuración · carga y validación de los parámetros.

Este módulo es la **única fuente operativa** de los parámetros del sistema
(incremento 1, sección 3 del plan). La *regla* vive en Requerimientos V3 §6.1;
el *valor* vive solo en el archivo que nombra `NOMBRE_ARCHIVO`. Ningún otro
módulo repite estos valores: si el archivo cambia, el comportamiento cambia sin
tocar código.

Dos consecuencias de diseño:

1. Si al arrancar falta una llave obligatoria o su valor es incoherente, se
   levanta `ErrorDeConfiguracion` y el backend **no arranca en silencio**
   (prueba «UT-03 · configuración incompleta» de la sección 10).
2. El bloque `motor` (umbral de confianza y pesos de fusión) **no** es
   obligatorio: pertenece al incremento 3 y hoy no debe impedir el arranque.

Este módulo no depende de UT-02: UT-02 construye sus mensajes a partir de estos
parámetros, así que la dependencia va en un solo sentido.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: Carpeta de UT-03 dentro del repositorio.
CARPETA: Path = Path(__file__).resolve().parent

#: Nombre del archivo de parámetros (D-6). Va versionado en el repositorio y
#: **no** lleva sufijo `.ejemplo`: ese sufijo es convención de «plantilla para
#: copiar» y aquí engañaba, porque este archivo *es* la fuente operativa.
#:
#: El nombre vive solo aquí: `cargador.py` y las pruebas lo leen de esta
#: constante, así un renombre futuro toca una sola línea.
NOMBRE_ARCHIVO: str = "parametros.json"

#: Patrón para detectar variantes del archivo de parámetros. D-6 exige que haya
#: exactamente una: si aparece una segunda, alguna deja de ser la fuente y la
#: decisión hay que volverla a tomar.
PATRON_ARCHIVO: str = "parametros*.json"

#: Ruta completa del archivo de parámetros.
RUTA_PARAMETROS: Path = CARPETA / NOMBRE_ARCHIVO


class ErrorDeConfiguracion(Exception):
    """La configuración falta, no se puede leer o es incoherente.

    Es un error de arranque, no un rechazo de negocio: el usuario final nunca lo
    ve. La capa HTTP lo traduce al mensaje `CONFIGURACION_INCOMPLETA` de UT-02.
    """


@dataclass(frozen=True)
class ParametrosArchivo:
    """Parámetros que usa MOD-02 (manejador de archivos)."""

    tamano_maximo_bytes: int
    formatos_permitidos: tuple[str, ...]


@dataclass(frozen=True)
class ParametrosValidacion:
    """Parámetros que usa MOD-03 (validador)."""

    puntos_minimos: int
    rango_requerido_cm1: tuple[float, float]
    jcamp_etiquetas_obligatorias: tuple[str, ...]
    jcamp_etiquetas_datos_una_de: tuple[str, ...]


@dataclass(frozen=True)
class ParametrosProcesamiento:
    """Parámetros que usa MOD-04 (procesador de espectros) desde el incremento 2.

    La rejilla es el contrato con MOD-05 y MOD-06: todo espectro sale con
    puntos_rejilla valores, repartidos de forma pareja en rango_rejilla_cm1.
    """

    puntos_rejilla: int
    rango_rejilla_cm1: tuple[float, float]


@dataclass(frozen=True)
class Configuracion:
    """Los parámetros ya validados, listos para usarse."""

    archivo: ParametrosArchivo
    validacion: ParametrosValidacion
    procesamiento: ParametrosProcesamiento
    ruta: Path


# --------------------------------------------------------------------------- #
# Validación de llaves
# --------------------------------------------------------------------------- #

_ACCION = "Corrija el archivo de parámetros de UT-03 y vuelva a iniciar el backend."


def _error(detalle: str, ruta: Path) -> ErrorDeConfiguracion:
    return ErrorDeConfiguracion(f"UT-03: {detalle} (archivo: {ruta}). {_ACCION}")


def _bloque(datos: dict[str, Any], nombre: str, ruta: Path) -> dict[str, Any]:
    if nombre not in datos:
        raise _error(f"falta el bloque obligatorio «{nombre}»", ruta)
    valor = datos[nombre]
    if not isinstance(valor, dict):
        raise _error(
            f"el bloque «{nombre}» debe ser un objeto con sus llaves dentro", ruta
        )
    return valor


def _presente(bloque: dict[str, Any], llave: str, ruta: Path, prefijo: str) -> Any:
    if llave not in bloque:
        raise _error(f"falta la llave obligatoria «{prefijo}.{llave}»", ruta)
    return bloque[llave]


def _entero_positivo(
    bloque: dict[str, Any], llave: str, ruta: Path, prefijo: str
) -> int:
    valor = _presente(bloque, llave, ruta, prefijo)
    # `bool` es subclase de `int` en Python: sin esta guarda, `true` pasaría por
    # un entero válido.
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise _error(
            f"«{prefijo}.{llave}» debe ser un número entero, "
            f"no {type(valor).__name__}",
            ruta,
        )
    if valor <= 0:
        raise _error(f"«{prefijo}.{llave}» debe ser mayor que cero, no {valor}", ruta)
    return valor


def _lista_de_textos(
    bloque: dict[str, Any],
    llave: str,
    ruta: Path,
    prefijo: str,
    *,
    empieza_con: str | None = None,
    normalizar: bool = False,
) -> tuple[str, ...]:
    valor = _presente(bloque, llave, ruta, prefijo)
    if not isinstance(valor, list):
        raise _error(f"«{prefijo}.{llave}» debe ser una lista", ruta)
    if not valor:
        raise _error(f"«{prefijo}.{llave}» no puede estar vacía", ruta)

    textos: list[str] = []
    for elemento in valor:
        if not isinstance(elemento, str) or not elemento.strip():
            raise _error(
                f"«{prefijo}.{llave}» debe contener solo textos no vacíos; "
                f"se encontró {elemento!r}",
                ruta,
            )
        texto = elemento.strip()
        if empieza_con is not None and not texto.startswith(empieza_con):
            raise _error(
                f"«{prefijo}.{llave}» debe contener valores que empiecen con "
                f"«{empieza_con}»; se encontró {texto!r}",
                ruta,
            )
        textos.append(texto.lower() if normalizar else texto)

    if len(set(textos)) != len(textos):
        raise _error(f"«{prefijo}.{llave}» tiene valores repetidos", ruta)
    return tuple(textos)


def _rango(
    bloque: dict[str, Any], llave: str, ruta: Path, prefijo: str
) -> tuple[float, float]:
    valor = _presente(bloque, llave, ruta, prefijo)
    if not isinstance(valor, list) or len(valor) != 2:
        raise _error(
            f"«{prefijo}.{llave}» debe ser una lista de dos números "
            f"[mínimo, máximo]",
            ruta,
        )

    numeros: list[float] = []
    for elemento in valor:
        if isinstance(elemento, bool) or not isinstance(elemento, (int, float)):
            raise _error(
                f"«{prefijo}.{llave}» debe contener solo números; "
                f"se encontró {elemento!r}",
                ruta,
            )
        numeros.append(float(elemento))

    minimo, maximo = numeros
    if minimo <= 0 or maximo <= 0:
        raise _error(f"«{prefijo}.{llave}» debe tener números de onda positivos", ruta)
    if minimo >= maximo:
        raise _error(
            f"«{prefijo}.{llave}» está invertido: el mínimo ({minimo:g}) debe ser "
            f"menor que el máximo ({maximo:g})",
            ruta,
        )
    return minimo, maximo


# --------------------------------------------------------------------------- #
# Carga
# --------------------------------------------------------------------------- #


def cargar(ruta: Path | str | None = None) -> Configuracion:
    """Lee y valida el archivo de parámetros.

    Args:
        ruta: archivo a leer. Si es ``None`` se usa `RUTA_PARAMETROS`, el
            archivo del repositorio. El parámetro existe para las pruebas y
            para entornos que apunten a otra copia; la aplicación no lo pasa.

    Returns:
        La configuración validada.

    Raises:
        ErrorDeConfiguracion: si el archivo no existe, no es JSON válido, le
            falta una llave obligatoria o algún valor es incoherente.
    """
    ruta_final = Path(ruta) if ruta is not None else RUTA_PARAMETROS

    if not ruta_final.is_file():
        raise _error("no se encontró el archivo de parámetros", ruta_final)

    try:
        contenido = ruta_final.read_text(encoding="utf-8")
    except OSError as error:
        raise _error(
            f"no se pudo leer el archivo ({error.strerror})", ruta_final
        ) from error

    try:
        datos = json.loads(contenido)
    except json.JSONDecodeError as error:
        raise _error(
            f"el archivo no es JSON válido (línea {error.lineno}, "
            f"columna {error.colno})",
            ruta_final,
        ) from error

    if not isinstance(datos, dict):
        raise _error("el archivo debe contener un objeto JSON en su raíz", ruta_final)

    bloque_archivo = _bloque(datos, "archivo", ruta_final)
    bloque_validacion = _bloque(datos, "validacion", ruta_final)
    bloque_procesamiento = _bloque(datos, "procesamiento", ruta_final)

    parametros_archivo = ParametrosArchivo(
        tamano_maximo_bytes=_entero_positivo(
            bloque_archivo, "tamano_maximo_bytes", ruta_final, "archivo"
        ),
        formatos_permitidos=_lista_de_textos(
            bloque_archivo,
            "formatos_permitidos",
            ruta_final,
            "archivo",
            empieza_con=".",
            normalizar=True,
        ),
    )

    parametros_validacion = ParametrosValidacion(
        puntos_minimos=_entero_positivo(
            bloque_validacion, "puntos_minimos", ruta_final, "validacion"
        ),
        rango_requerido_cm1=_rango(
            bloque_validacion, "rango_requerido_cm1", ruta_final, "validacion"
        ),
        jcamp_etiquetas_obligatorias=_lista_de_textos(
            bloque_validacion, "jcamp_etiquetas_obligatorias", ruta_final, "validacion"
        ),
        jcamp_etiquetas_datos_una_de=_lista_de_textos(
            bloque_validacion, "jcamp_etiquetas_datos_una_de", ruta_final, "validacion"
        ),
    )

    puntos_rejilla = _entero_positivo(
        bloque_procesamiento, "puntos_rejilla", ruta_final, "procesamiento"
    )
    if puntos_rejilla < 2:
        raise _error(
            "«procesamiento.puntos_rejilla» necesita al menos dos puntos para "
            "formar un eje",
            ruta_final,
        )
    parametros_procesamiento = ParametrosProcesamiento(
        puntos_rejilla=puntos_rejilla,
        rango_rejilla_cm1=_rango(
            bloque_procesamiento, "rango_rejilla_cm1", ruta_final, "procesamiento"
        ),
    )

    return Configuracion(
        archivo=parametros_archivo,
        validacion=parametros_validacion,
        procesamiento=parametros_procesamiento,
        ruta=ruta_final,
    )


_configuracion: Configuracion | None = None


def obtener() -> Configuracion:
    """Devuelve la configuración, leyendo el archivo la primera vez.

    Es la puerta que usan los demás módulos (MOD-02, MOD-03, UT-02). El
    resultado se guarda en memoria: el archivo es de solo lectura y no cambia
    mientras el backend corre.
    """
    global _configuracion
    if _configuracion is None:
        _configuracion = cargar()
    return _configuracion


def recargar(ruta: Path | str | None = None) -> Configuracion:
    """Vuelve a leer el archivo y reemplaza lo que haya en memoria.

    Pensado para las pruebas y para verificar en vivo que cambiar un valor del
    archivo cambia el comportamiento del sistema.
    """
    global _configuracion
    _configuracion = cargar(ruta)
    return _configuracion
