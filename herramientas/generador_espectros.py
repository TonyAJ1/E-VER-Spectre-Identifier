"""Generador de espectros sintéticos para las pruebas del incremento 1.

**Esto no es código de la aplicación.** Vive en `herramientas/` a propósito: es
una herramienta de preparación de datos de prueba. No lo importe ningún módulo
de `backend/`, y no se vuelva la base de MOD-04 sin revisarlo (sección 11 del
plan).

El incremento 1 solo valida **estructura, tamaño, puntos y rango**: nunca mira
química real. Por eso sus archivos de prueba son fabricados, sin una sola línea
de datos de NIST. Eso cubre todas las CA del incremento, evita el problema de
redistribución del repositorio público y deja que cualquiera corra las pruebas
sin descargar nada.

Los valores que importan —tamaño máximo y puntos mínimos— se leen de UT-03, no
se escriben aquí: si el equipo cambia el límite, los archivos de prueba lo
siguen.
"""

from __future__ import annotations

import struct
import zlib

#: Formato de cada par del CSV. Dos columnas: número de onda, intensidad.
_FORMATO_CSV = "{x:.4f},{y:.6f}"

#: Formato de ancho fijo, con el número de onda rellenado con ceros a la
#: izquierda («0400.0000»). Solo lo usa el archivo de tamaño exacto: con todas
#: las líneas del mismo largo, el relleno final es de unos pocos bytes en vez de
#: decenas de miles. Los ceros a la izquierda no estorban: sigue siendo un
#: número.
_FORMATO_CSV_FIJO = "{x:09.4f},{y:.6f}"


def _intensidad(indice: int, puntos: int) -> float:
    """Una curva suave y determinista, entre 0 y 1.

    No pretende parecerse a un espectro real: solo necesita ser un número
    plausible de transmitancia. La forma es determinista para que el archivo
    generado sea idéntico en cada corrida y git no vea cambios falsos.
    """
    fraccion = indice / max(puntos - 1, 1)
    # Dos «jorobas» mezcladas, sin usar módulos externos.
    joroba = 0.35 + 0.45 * abs(0.5 - fraccion) * 2
    rizo = 0.08 * ((indice * 7919) % 101) / 100
    return round(min(max(joroba + rizo, 0.01), 0.99), 6)


def _numeros_de_onda(puntos: int, desde: float, hasta: float) -> list[float]:
    if puntos < 2:
        raise ValueError("se necesitan al menos dos puntos")
    paso = (hasta - desde) / (puntos - 1)
    return [desde + indice * paso for indice in range(puntos)]


def csv_sintetico(
    puntos: int,
    desde: float,
    hasta: float,
    *,
    encabezado: str | None = None,
    en_porcentaje: bool = False,
    valor_fijo: float | None = None,
) -> bytes:
    """Un CSV de dos columnas con `puntos` pares, de `desde` a `hasta` cm⁻¹.

    Sin argumentos extra da el mismo archivo de siempre. Con `encabezado` la
    primera fila lleva ese texto. Con `en_porcentaje` la intensidad sale
    multiplicada por cien, como la exporta un equipo que mide transmitancia en
    porcentaje. Con `valor_fijo` todas las intensidades valen lo mismo, que es
    la línea plana del incremento 2.
    """
    lineas = [encabezado] if encabezado else []
    for indice, x in enumerate(_numeros_de_onda(puntos, desde, hasta)):
        y = valor_fijo if valor_fijo is not None else _intensidad(indice, puntos)
        if en_porcentaje:
            lineas.append(f"{x:.4f},{y * 100:.4f}")
        else:
            lineas.append(_FORMATO_CSV.format(x=x, y=y))
    return ("\n".join(lineas) + "\n").encode("ascii")


def csv_de_tamano_exacto(
    bytes_objetivo: int, desde: float, hasta: float, *, puntos_minimos: int
) -> bytes:
    """Un CSV válido que pesa **exactamente** `bytes_objetivo`.

    Es lo único que no puede existir «en la naturaleza»: un espectro de un
    tamaño al byte. Se arma con tantos pares como quepan y se rellena la última
    intensidad con decimales de más —sigue siendo un número válido— hasta dar
    el tamaño exacto.

    Args:
        bytes_objetivo: tamaño final del archivo, en bytes.
        desde: primer número de onda.
        hasta: último número de onda.
        puntos_minimos: cantidad de pares por debajo de la cual el archivo no
            serviría para la prueba (se toma de UT-03).

    Raises:
        ValueError: si el tamaño pedido no alcanza para los puntos mínimos.
    """
    largo_linea = len(_FORMATO_CSV_FIJO.format(x=hasta, y=0.123456)) + 1
    puntos = max(bytes_objetivo // largo_linea, puntos_minimos)

    # Se arma dejando la última línea para el final: ahí va el relleno.
    while True:
        ondas = _numeros_de_onda(puntos, desde, hasta)
        cuerpo = "\n".join(
            _FORMATO_CSV_FIJO.format(x=x, y=_intensidad(indice, puntos))
            for indice, x in enumerate(ondas[:-1])
        )
        cuerpo = (cuerpo + "\n").encode("ascii") if cuerpo else b""
        ultima = _FORMATO_CSV_FIJO.format(x=ondas[-1], y=_intensidad(puntos - 1, puntos))
        faltan = bytes_objetivo - len(cuerpo) - len(ultima.encode("ascii")) - 1

        if faltan >= 0:
            break
        puntos -= 1
        if puntos < puntos_minimos:
            raise ValueError(
                f"{bytes_objetivo} bytes no alcanzan para {puntos_minimos} pares"
            )

    # El relleno son decimales extra de la última intensidad: el par sigue
    # siendo «número, número».
    archivo = cuerpo + (ultima + "0" * faltan + "\n").encode("ascii")

    if len(archivo) != bytes_objetivo:  # pragma: no cover - red de seguridad
        raise AssertionError(
            f"se pidieron {bytes_objetivo} bytes y salieron {len(archivo)}"
        )
    if puntos < puntos_minimos:  # pragma: no cover - red de seguridad
        raise AssertionError(f"quedaron {puntos} pares, menos que el mínimo")
    return archivo


def jdx_sintetico(
    titulo: str,
    puntos: int,
    desde: float,
    hasta: float,
    *,
    nota: str = "",
    con_end: bool = True,
    descendente: bool = False,
) -> bytes:
    """Un `.jdx` con las etiquetas obligatorias y pares bajo `##XYDATA=`.

    `##TITLE=` queda en la primera línea y `##END=` en la última, como exige
    MOD-03. Con `con_end=False` se obtiene el archivo truncado de CA-02.4. Con
    `descendente=True` los mismos puntos se escriben de 4000 hacia 400, que es
    el caso de CA-03.2.

    La nota se escribe como comentario `$$`, que es parte del formato
    JCAMP-DX, así que el archivo sigue siendo válido.
    """
    lineas = [
        f"##TITLE={titulo}",
        "##JCAMP-DX=4.24",
        "##DATA TYPE=INFRARED SPECTRUM",
    ]
    if nota:
        lineas.append(f"$$ {nota}")
    lineas += [
        "##ORIGIN=E-VER Spectre Identifier (archivo fabricado para pruebas)",
        "##OWNER=PUBLIC DOMAIN",
        "##XUNITS=1/CM",
        "##YUNITS=TRANSMITTANCE",
        "##XFACTOR=1",
        "##YFACTOR=1",
        f"##FIRSTX={hasta if descendente else desde:.4f}",
        f"##LASTX={desde if descendente else hasta:.4f}",
        f"##NPOINTS={puntos}",
        "##XYDATA=(XY..XY)",
    ]
    datos = [
        f"{x:.4f} {_intensidad(indice, puntos):.6f}"
        for indice, x in enumerate(_numeros_de_onda(puntos, desde, hasta))
    ]
    lineas += list(reversed(datos)) if descendente else datos
    if con_end:
        lineas.append("##END=")
    return ("\n".join(lineas) + "\n").encode("ascii")


def png_minimo() -> bytes:
    """Un PNG válido de 1×1 píxel, armado a mano.

    Sirve para CA-01.3: un formato que la aplicación no admite. Se fabrica con
    la biblioteca estándar para no agregar dependencias de imágenes.
    """

    def trozo(tipo: bytes, datos: bytes) -> bytes:
        crc = zlib.crc32(tipo + datos) & 0xFFFFFFFF
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", crc)

    firma = b"\x89PNG\r\n\x1a\n"
    # 1×1, 8 bits, escala de grises.
    cabecera = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    pixeles = zlib.compress(b"\x00\x00")
    return firma + trozo(b"IHDR", cabecera) + trozo(b"IDAT", pixeles) + trozo(b"IEND", b"")


def binario_disfrazado() -> bytes:
    """Bytes binarios con la cabecera «MZ», para renombrarlos a `.csv`.

    Sirve para CA-02.5: la aplicación debe rechazarlo **por su contenido**, sin
    confiar en la extensión. **No es un ejecutable:** son bytes nulos y un
    relleno determinista detrás de la cabecera, sin cabecera PE válida ni una
    sola instrucción. No puede ejecutarse ni en Windows ni en ningún otro
    sistema; lo único que importa para la prueba es que traiga bytes nulos y no
    imprimibles.
    """
    relleno = bytes((indice * 37 + 11) % 256 for indice in range(512))
    return b"MZ" + b"\x00" * 60 + relleno


# Archivos JCAMP-DX con factores de escala y con datos comprimidos. Los usa el
# incremento 2 para probar que MOD-04 lee bien lo que traen los archivos de
# NIST, sin copiar un solo dato de NIST.


def _encabezado_jdx(
    titulo: str, nota: str, puntos: int, desde: float, hasta: float,
    xfactor: str, yfactor: str, forma: str,
) -> list[str]:
    return [
        f"##TITLE={titulo}",
        "##JCAMP-DX=4.24",
        "##DATA TYPE=INFRARED SPECTRUM",
        f"$$ {nota}",
        "##ORIGIN=E-VER Spectre Identifier (archivo fabricado para pruebas)",
        "##OWNER=PUBLIC DOMAIN",
        "##XUNITS=1/CM",
        "##YUNITS=TRANSMITTANCE",
        f"##XFACTOR={xfactor}",
        f"##YFACTOR={yfactor}",
        f"##FIRSTX={desde:.4f}",
        f"##LASTX={hasta:.4f}",
        f"##NPOINTS={puntos}",
        f"##XYDATA={forma}",
    ]


def jdx_con_factores(
    titulo: str, puntos: int, desde: float, hasta: float, *, nota: str
) -> bytes:
    """Los mismos puntos de `jdx_sintetico`, guardados con YFACTOR de 0.001.

    Cada intensidad se escribe multiplicada por mil. Quien lea el archivo y no
    aplique el factor verá valores mil veces más grandes, que es justo el error
    que la prueba quiere atrapar.
    """
    lineas = _encabezado_jdx(
        titulo, nota, puntos, desde, hasta, "1", "0.001", "(XY..XY)"
    )
    lineas += [
        f"{x:.4f} {_intensidad(indice, puntos) * 1000:.3f}"
        for indice, x in enumerate(_numeros_de_onda(puntos, desde, hasta))
    ]
    lineas.append("##END=")
    return ("\n".join(lineas) + "\n").encode("ascii")


#: Letras de la compresión de JCAMP-DX. En la forma SQZ la primera cifra de
#: un número absoluto se cambia por una letra que también lleva el signo. En
#: la forma DIF se guarda la diferencia con el valor anterior. En la forma DUP
#: una letra dice cuántas veces se repite lo último.
_SQZ_POSITIVO = "@ABCDEFGHI"
_SQZ_NEGATIVO = "@abcdefghi"
_DIF_POSITIVO = "%JKLMNOPQR"
_DIF_NEGATIVO = "%jklmnopqr"
_DUP = "STUVWXYZs"


def _con_letra(numero: int, positivas: str, negativas: str) -> str:
    cifras = str(abs(numero))
    letras = negativas if numero < 0 else positivas
    return letras[int(cifras[0])] + cifras[1:]


def _repeticion(veces: int) -> str:
    cifras = str(veces)
    return _DUP[int(cifras[0]) - 1] + cifras[1:]


def _linea_difdup(valores: list[int]) -> str:
    """Una línea de datos en forma DIFDUP, sin el número de onda del inicio."""
    piezas = [_con_letra(valores[0], _SQZ_POSITIVO, _SQZ_NEGATIVO)]
    diferencias = [b - a for a, b in zip(valores, valores[1:])]
    indice = 0
    while indice < len(diferencias):
        actual = diferencias[indice]
        veces = 1
        while (
            indice + veces < len(diferencias)
            and diferencias[indice + veces] == actual
        ):
            veces += 1
        piezas.append(_con_letra(actual, _DIF_POSITIVO, _DIF_NEGATIVO))
        if veces > 1:
            piezas.append(_repeticion(veces))
        indice += veces
    return "".join(piezas)


def jdx_comprimido(
    titulo: str,
    puntos: int,
    desde: float,
    hasta: float,
    *,
    nota: str,
    por_linea: int = 10,
) -> bytes:
    """Los mismos puntos de `jdx_sintetico`, comprimidos como los guarda NIST.

    Usa la forma (X++(Y..Y)) con DIFDUP. Las intensidades se guardan como
    enteros y YFACTOR las regresa a su valor. Cada línea empieza con el
    número de onda de su primer valor, también entero gracias a XFACTOR. Como
    pide la norma, a partir de la segunda línea el primer valor repite el
    último de la línea anterior para poder comprobar que nada se perdió.
    """
    ondas = _numeros_de_onda(puntos, desde, hasta)
    enteros = [round(_intensidad(indice, puntos) * 1_000_000) for indice in range(puntos)]

    lineas = _encabezado_jdx(
        titulo, nota, puntos, desde, hasta, "0.0001", "0.000001", "(X++(Y..Y))"
    )
    inicio = 0
    while inicio < puntos:
        fin = min(inicio + por_linea, puntos)
        desde_aqui = inicio if inicio == 0 else inicio - 1
        x_entero = round(ondas[desde_aqui] * 10_000)
        lineas.append(f"{x_entero}{_linea_difdup(enteros[desde_aqui:fin])}")
        inicio = fin
    lineas.append("##END=")
    return ("\n".join(lineas) + "\n").encode("ascii")
