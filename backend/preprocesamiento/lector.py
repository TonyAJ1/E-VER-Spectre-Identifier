"""Lector de espectros de MOD-04 (tarea T-08).

Convierte el texto de un archivo .jdx o .csv en una lista de pares con el
número de onda y la intensidad. Los dos formatos terminan en la misma forma,
así que el resto de MOD-04 ya no necesita saber de dónde vino el espectro.

MOD-03 ya revisó el archivo antes de que llegue aquí, pero solo con una
lectura ligera del encabezado. Esta es la lectura completa: aplica los
factores de escala, descomprime los datos de JCAMP-DX y comprueba que salgan
tantos puntos como dice el encabezado. Si algo no cuadra, el archivo se
rechaza con el código DATOS_ILEGIBLES de UT-02. Nunca se devuelven valores
dudosos en silencio.

El contenido llega como texto y se queda en memoria. Este módulo no escribe
nada en disco ni guarda el espectro en el registro.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

#: Unidades de intensidad que entiende MOD-04. Cuando un CSV no dice en qué
#: unidad viene, se marca como desconocida y T-09 la decide por los valores.
ABSORBANCIA = "absorbancia"
TRANSMITANCIA = "transmitancia"
DESCONOCIDA = "desconocida"

EXTENSION_JDX = ".jdx"
EXTENSION_CSV = ".csv"


class ArchivoIlegible(Exception):
    """Los datos del archivo no se pueden leer con seguridad.

    El texto de la excepción es para el equipo y para el registro. Nunca lleva
    valores del espectro y nunca se le muestra al usuario, que recibe el
    mensaje de UT-02.
    """


@dataclass(frozen=True)
class Lectura:
    """Lo que sale de leer un archivo.

    pares trae el número de onda en cm⁻¹ y la intensidad ya multiplicada por
    sus factores, en el mismo orden en que venían en el archivo. unidad dice si
    la intensidad es absorbancia, transmitancia o si no se sabe.
    """

    pares: tuple[tuple[float, float], ...]
    unidad: str


def leer(nombre: str, contenido: str) -> Lectura:
    """Lee el archivo según su extensión.

    Levanta ArchivoIlegible si la extensión no es una de las dos que sabe leer
    o si los datos no se pueden interpretar.
    """
    extension = _extension(nombre)
    if extension == EXTENSION_JDX:
        return leer_jdx(contenido)
    if extension == EXTENSION_CSV:
        return leer_csv(contenido)
    raise ArchivoIlegible("MOD-04 no sabe leer archivos con esa extensión")


def _extension(nombre: str) -> str:
    punto = nombre.rfind(".")
    return nombre[punto:].lower() if punto > 0 else ""


# Lectura del CSV
#
# El formato sale de los Requerimientos: dos columnas numéricas, una fila de
# encabezado opcional y separador de coma o de punto y coma. Con punto y coma el
# decimal puede venir con coma, como lo guarda Excel en español.

_LETRA = re.compile(r"[^\W\d_]")


def leer_csv(contenido: str) -> Lectura:
    pares: list[tuple[float, float]] = []
    separador: str | None = None
    encabezado = ""

    for linea in contenido.splitlines():
        if not linea.strip():
            continue
        if separador is None:
            separador = ";" if ";" in linea else ","

        campos = [campo.strip() for campo in linea.split(separador)]
        par = _par_csv(campos, separador)
        if par is None:
            if not pares and not encabezado and _LETRA.search(linea):
                encabezado = linea
                continue
            raise ArchivoIlegible("una fila del CSV no trae dos números")
        pares.append(par)

    if not pares:
        raise ArchivoIlegible("el CSV no trae datos")
    return Lectura(tuple(pares), _unidad_del_encabezado(encabezado))


def _par_csv(campos: list[str], separador: str) -> tuple[float, float] | None:
    if len(campos) != 2:
        return None
    if separador == ";":
        campos = [campo.replace(",", ".") for campo in campos]
    try:
        onda, intensidad = float(campos[0]), float(campos[1])
    except ValueError:
        return None
    if not (math.isfinite(onda) and math.isfinite(intensidad)):
        return None
    return onda, intensidad


def _unidad_del_encabezado(encabezado: str) -> str:
    """Busca en el encabezado del CSV una pista de la unidad.

    Se aceptan palabras en español y en inglés, y también la forma corta %T.
    Si no hay pista, la unidad queda como desconocida.
    """
    texto = encabezado.lower()
    if "absorb" in texto:
        return ABSORBANCIA
    if "transm" in texto or "%t" in texto:
        return TRANSMITANCIA
    return DESCONOCIDA


# Lectura de JCAMP-DX
#
# Se leen las etiquetas del encabezado y después el bloque de datos. Hay dos
# formas de bloque. En (XY..XY) cada número de onda va junto a su intensidad.
# En (X++(Y..Y)) cada línea empieza con un número de onda y le siguen varias
# intensidades seguidas, y es la forma en que suelen venir comprimidos los
# archivos de NIST.

_IGNORADO_EN_ETIQUETAS = re.compile(r"[\s\-_/]")
_FORMA_PARES = "(XY..XY)"
_FORMA_SEGUIDA = "(X++(Y..Y))"
_ETIQUETAS_DE_DATOS = ("XYDATA", "PEAKTABLE")


def leer_jdx(contenido: str) -> Lectura:
    etiquetas, forma, lineas = _partes_jdx(contenido)

    unidad_x = etiquetas.get("XUNITS", "").upper()
    if unidad_x and "CM" not in unidad_x:
        raise ArchivoIlegible("el eje no viene en número de onda (1/CM)")

    factor_x = _numero(etiquetas, "XFACTOR", 1.0)
    factor_y = _numero(etiquetas, "YFACTOR", 1.0)
    puntos_declarados = etiquetas.get("NPOINTS")

    forma_limpia = forma.replace(" ", "").upper()
    if forma_limpia == _FORMA_SEGUIDA:
        pares = _leer_seguida(lineas, etiquetas, factor_y)
    elif forma_limpia == _FORMA_PARES or forma_limpia.startswith("(XY"):
        pares = _leer_pares(lineas, factor_x, factor_y)
    else:
        raise ArchivoIlegible("la forma del bloque de datos no es una que se conozca")

    if puntos_declarados is not None:
        esperados = _entero(puntos_declarados, "NPOINTS")
        if len(pares) != esperados:
            raise ArchivoIlegible(
                f"se leyeron {len(pares)} puntos y el encabezado dice {esperados}"
            )

    return Lectura(tuple(pares), _unidad_jdx(etiquetas.get("YUNITS", "")))


def _partes_jdx(contenido: str) -> tuple[dict[str, str], str, list[str]]:
    """Separa las etiquetas, la forma del bloque de datos y sus líneas."""
    etiquetas: dict[str, str] = {}
    forma = ""
    lineas: list[str] = []
    dentro_de_datos = False

    for linea in contenido.splitlines():
        sin_comentario = linea.split("$$", 1)[0].strip()
        if not sin_comentario:
            continue
        if sin_comentario.startswith("##"):
            if dentro_de_datos:
                break
            nombre, _, valor = sin_comentario[2:].partition("=")
            nombre = _IGNORADO_EN_ETIQUETAS.sub("", nombre).upper()
            if nombre in _ETIQUETAS_DE_DATOS:
                forma = valor.strip()
                dentro_de_datos = True
                continue
            etiquetas.setdefault(nombre, valor.strip())
            continue
        if dentro_de_datos:
            lineas.append(sin_comentario)

    if not dentro_de_datos or not lineas:
        raise ArchivoIlegible("no se encontró el bloque de datos")
    return etiquetas, forma, lineas


def _numero(etiquetas: dict[str, str], nombre: str, si_falta: float) -> float:
    if nombre not in etiquetas:
        return si_falta
    try:
        valor = float(etiquetas[nombre])
    except ValueError as error:
        raise ArchivoIlegible(f"la etiqueta {nombre} no trae un número") from error
    if not math.isfinite(valor) or valor == 0:
        raise ArchivoIlegible(f"la etiqueta {nombre} trae un valor imposible")
    return valor


def _real(texto: str, nombre: str) -> float:
    try:
        valor = float(texto)
    except ValueError as error:
        raise ArchivoIlegible(f"la etiqueta {nombre} no trae un número") from error
    if not math.isfinite(valor):
        raise ArchivoIlegible(f"la etiqueta {nombre} trae un valor imposible")
    return valor


def _entero(texto: str, nombre: str) -> int:
    try:
        valor = float(texto)
    except ValueError as error:
        raise ArchivoIlegible(f"la etiqueta {nombre} no trae un número") from error
    if not math.isfinite(valor) or valor <= 0 or valor != int(valor):
        raise ArchivoIlegible(f"la etiqueta {nombre} trae un valor imposible")
    return int(valor)


def _unidad_jdx(unidad: str) -> str:
    texto = unidad.upper()
    if "ABSORB" in texto:
        return ABSORBANCIA
    if "TRANSM" in texto:
        return TRANSMITANCIA
    raise ArchivoIlegible("la intensidad no viene en absorbancia ni en transmitancia")


def _leer_pares(
    lineas: list[str], factor_x: float, factor_y: float
) -> list[tuple[float, float]]:
    """Forma (XY..XY): números sueltos que se toman de dos en dos."""
    numeros: list[float] = []
    for linea in lineas:
        for pieza in re.split(r"[\s,;]+", linea):
            if not pieza:
                continue
            try:
                numeros.append(float(pieza))
            except ValueError as error:
                raise ArchivoIlegible("un par de datos no se pudo leer") from error

    if len(numeros) % 2 != 0:
        raise ArchivoIlegible("los datos no vienen en pares completos")
    return [
        (numeros[i] * factor_x, numeros[i + 1] * factor_y)
        for i in range(0, len(numeros), 2)
    ]


def _leer_seguida(
    lineas: list[str], etiquetas: dict[str, str], factor_y: float
) -> list[tuple[float, float]]:
    """Forma (X++(Y..Y)), con o sin compresión.

    El número de onda de cada punto no se toma de las líneas sino de FIRSTX,
    LASTX y NPOINTS, que ya vienen en cm⁻¹. Es lo que recomienda la norma y
    evita errores de redondeo de un punto al siguiente.
    """
    for necesaria in ("FIRSTX", "LASTX", "NPOINTS"):
        if necesaria not in etiquetas:
            raise ArchivoIlegible(f"falta la etiqueta {necesaria}")
    primero = _real(etiquetas["FIRSTX"], "FIRSTX")
    ultimo = _real(etiquetas["LASTX"], "LASTX")
    puntos = _entero(etiquetas["NPOINTS"], "NPOINTS")

    valores = descomprimir(lineas)
    if len(valores) != puntos:
        raise ArchivoIlegible(
            f"se leyeron {len(valores)} puntos y el encabezado dice {puntos}"
        )

    paso = (ultimo - primero) / (puntos - 1) if puntos > 1 else 0.0
    return [(primero + i * paso, valor * factor_y) for i, valor in enumerate(valores)]


# Descompresión de JCAMP-DX
#
# La norma guarda los números de cuatro maneras que se pueden mezclar en una
# misma línea:
#
# AFFN y PAC son números comunes, separados por espacios, comas o por su signo.
# SQZ cambia la primera cifra por una letra: @ es 0, de A a I son 1 a 9 y de
#   a a i son -1 a -9.
# DIF guarda la diferencia con el valor anterior: % es 0, de J a R son 1 a 9 y
#   de j a r son -1 a -9.
# DUP dice cuántas veces aparece lo último: de S a Z son 1 a 8 y s es 9.
#
# Cuando una línea termina con una diferencia, la siguiente empieza repitiendo
# el último valor para comprobar que no se perdió nada. Ese valor repetido se
# compara y se descarta.

_SQZ = {"@": 0, **{c: i + 1 for i, c in enumerate("ABCDEFGHI")},
        **{c: -(i + 1) for i, c in enumerate("abcdefghi")}}
_DIF = {"%": 0, **{c: i + 1 for i, c in enumerate("JKLMNOPQR")},
        **{c: -(i + 1) for i, c in enumerate("jklmnopqr")}}
_DUP = {**{c: i + 1 for i, c in enumerate("STUVWXYZ")}, "s": 9}

_ABSOLUTO = "absoluto"
_DIFERENCIA = "diferencia"
_REPETICION = "repeticion"

#: Margen para comparar el valor de comprobación. Los valores comprimidos son
#: enteros, pero en la forma común pueden traer decimales.
_MARGEN_COMPROBACION = 1e-6


def _piezas(linea: str) -> list[tuple[str, float]]:
    """Parte una línea en números absolutos, diferencias y repeticiones."""
    piezas: list[tuple[str, float]] = []
    i = 0
    largo = len(linea)
    while i < largo:
        c = linea[i]
        if c in " \t,;":
            i += 1
            continue

        if c in _SQZ:
            tipo, inicio, signo_y_cifra = _ABSOLUTO, c, _SQZ[c]
        elif c in _DIF:
            tipo, inicio, signo_y_cifra = _DIFERENCIA, c, _DIF[c]
        elif c in _DUP:
            tipo, inicio, signo_y_cifra = _REPETICION, c, _DUP[c]
        elif c.isdigit() or c in "+-.":
            tipo, inicio, signo_y_cifra = _ABSOLUTO, c, None
        else:
            raise ArchivoIlegible("los datos traen un carácter que no se reconoce")

        j = i + 1
        while j < largo and (linea[j].isdigit() or linea[j] == "."):
            j += 1
        # Exponente de un número común, como 1.5E+03. Solo se acepta con su
        # signo, porque una E sin signo es la letra SQZ del 5 y abre otro
        # número.
        if (
            signo_y_cifra is None
            and j + 2 < largo
            and linea[j] in "eE"
            and linea[j + 1] in "+-"
            and linea[j + 2].isdigit()
        ):
            j += 2
            while j < largo and linea[j].isdigit():
                j += 1

        resto = linea[i + 1 : j]
        if signo_y_cifra is None:
            texto = inicio + resto
        else:
            signo = "-" if signo_y_cifra < 0 else ""
            texto = f"{signo}{abs(signo_y_cifra)}{resto}"
        try:
            valor = float(texto)
        except ValueError as error:
            raise ArchivoIlegible("un número de los datos no se pudo leer") from error
        piezas.append((tipo, valor))
        i = j
    return piezas


def descomprimir(lineas: list[str]) -> list[float]:
    """Las intensidades de un bloque (X++(Y..Y)), sin factores todavía.

    El primer número de cada línea es el número de onda y se descarta aquí,
    porque el eje se calcula aparte.
    """
    valores: list[float] = []
    venia_en_diferencias = False

    for linea in lineas:
        piezas = _piezas(linea)
        if not piezas:
            continue
        if piezas[0][0] != _ABSOLUTO:
            raise ArchivoIlegible("una línea de datos no empieza con su número de onda")

        de_esta_linea: list[float] = []
        ultima: tuple[str, float] | None = None
        for tipo, valor in piezas[1:]:
            if tipo == _ABSOLUTO:
                de_esta_linea.append(valor)
                ultima = (tipo, valor)
            elif tipo == _DIFERENCIA:
                if not de_esta_linea:
                    raise ArchivoIlegible("una diferencia no tiene valor de partida")
                de_esta_linea.append(de_esta_linea[-1] + valor)
                ultima = (tipo, valor)
            else:
                if ultima is None or valor < 2 or valor != int(valor):
                    raise ArchivoIlegible("una repetición no tiene qué repetir")
                for _ in range(int(valor) - 1):
                    if ultima[0] == _ABSOLUTO:
                        de_esta_linea.append(ultima[1])
                    else:
                        de_esta_linea.append(de_esta_linea[-1] + ultima[1])

        if venia_en_diferencias and valores and de_esta_linea:
            if abs(de_esta_linea[0] - valores[-1]) > _MARGEN_COMPROBACION:
                raise ArchivoIlegible("el valor de comprobación de una línea no coincide")
            de_esta_linea = de_esta_linea[1:]

        valores.extend(de_esta_linea)
        venia_en_diferencias = ultima is not None and ultima[0] == _DIFERENCIA

    if not valores:
        raise ArchivoIlegible("el bloque de datos no trae valores")
    return valores
