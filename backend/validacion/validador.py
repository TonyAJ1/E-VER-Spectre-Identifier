"""MOD-03 · Validador · ¿es este formato? (T-04) y ¿cumple los requisitos? (T-05)

Recibe lo que MOD-02 entrega —**contenido como texto**, nombre e indicador de
tamaño correcto (contrato de la sección 5)— y devuelve un **veredicto**: válido
sí o no y, si no, el código de UT-02 que explica el motivo.

El texto llega tal como lo dejó MOD-02: sin la marca de orden de bytes (BOM) y
con los bytes que no eran texto válido convertidos en el carácter de reemplazo
«�» (U+FFFD). Esa marca es justamente una de las pistas de la capa 1.

**Cuatro capas, en este orden**, cada una con su rechazo:

0. **Extensión** — tiene que estar en la lista de UT-03. Va primero a propósito:
   así un `.png` recibe el mensaje de formato (CA-01.3) y no el de «no es
   texto», que sería verdad pero no es lo que el usuario necesita oír.
1. **¿Es texto?** — bytes nulos, caracteres de control o marcas de reemplazo →
   rechazo inmediato. Es la defensa de RNF-03: nunca se interpreta binario.
2. **¿La estructura es la del formato declarado?** — `.jdx`: las etiquetas
   obligatorias de UT-03, con `##TITLE=` en la primera línea y `##END=` en la
   última, más una de las etiquetas de datos. `.csv`: las primeras filas
   parsean como pares numéricos, separados por coma o por punto y coma (con
   este último, el decimal puede venir con coma), con una fila de encabezado
   opcional (Requerimientos §6.1).
3. **Coherencia mínima** — que haya datos y que los números de onda sean
   positivos y utilizables.

**Lo que esta tarea no hace:**

- Las capas de T-04 no cuentan puntos ni miran el rango: eso es T-05, más
  abajo. Un espectro de pocos puntos o de rango corto **pasa** T-04 (la función
  `revisar_formato`), porque su formato sí es el que dice ser, y lo rechaza
  `validar`, que corre T-04 y después T-05.
- No normaliza, no ordena y no convierte: eso es MOD-04 (incremento 2). En
  particular **no se descifran las formas comprimidas de JCAMP-DX** (DIF, SQZ):
  interpretarlas es trabajo de MOD-04 y aquí solo se mira si hay datos y si el
  primer número de onda es plausible.
- No arma mensajes. Devuelve el **código**; el texto con motivo y acción lo pone
  UT-02, y lo traduce la capa HTTP (T-07) para los rechazos de MOD-02 y de
  MOD-03 en el mismo lugar.
- No importa MOD-02 ni nada de FastAPI: recibe texto, así se puede probar solo.

**T-05 · dos capas más**, solo si el formato pasó:

4. **Puntos** — al menos `validacion.puntos_minimos` de UT-03 (CA-02.6).
5. **Rango** — el mínimo y el máximo del número de onda tienen que cubrir
   `validacion.rango_requerido_cm1` de UT-03 (CA-02.3).

Es una **lectura ligera**. En el `.csv` se recorren todas las filas, se cuentan
los pares y se toma el mínimo y el máximo de la primera columna. En el `.jdx` se
leen `##NPOINTS=`, `##FIRSTX=` y `##LASTX=` del **encabezado**, sin descomprimir
el bloque de datos (eso es MOD-04); si faltan o no se leen, falla cerrado.

**Robustez (CA-02.4):** ninguna entrada hace que este módulo levante una
excepción. Un archivo vacío, truncado o lleno de basura sale por la puerta del
veredicto, con su motivo, y el servidor sigue atendiendo.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from dataclasses import dataclass

from backend.nucleo import obtener_registro
from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion

_registro = obtener_registro("mod-03")

# --------------------------------------------------------------------------- #
# Nombres de las capas · sirven para el registro y para las pruebas
# --------------------------------------------------------------------------- #

#: Freno de seguridad: MOD-02 no confirmó el tamaño (no debería ocurrir).
CAPA_TAMANO: str = "tamano"

#: Capa 0 · la extensión no está en la lista de UT-03.
CAPA_EXTENSION: str = "extension"

#: Capa 1 · el contenido no es texto.
CAPA_TEXTO: str = "texto"

#: Capa 2 · la estructura no es la del formato declarado.
CAPA_ESTRUCTURA: str = "estructura"

#: Capa 3 · la estructura está, pero los datos no son coherentes.
CAPA_COHERENCIA: str = "coherencia"

#: Capa 4 (T-05) · menos puntos que el mínimo de UT-03.
CAPA_PUNTOS: str = "puntos"

#: Capa 5 (T-05) · el número de onda no cubre el rango de UT-03.
CAPA_RANGO: str = "rango"

# --------------------------------------------------------------------------- #
# Parámetros de implementación
#
# Ninguno es valor de negocio: no son los de UT-03 (tamaño, formatos, puntos
# mínimos, rango, etiquetas), que se leen de la configuración. Estos solo dicen
# «cuánto hay que mirar para responder la pregunta de esta tarea».
# --------------------------------------------------------------------------- #

#: Cuántas filas del `.csv` se revisan. La pregunta de T-04 es «¿tiene forma de
#: este formato?», y eso se contesta con las primeras filas; recorrer el archivo
#: completo es trabajo de T-05, que además tiene que contar.
FILAS_A_REVISAR: int = 10

#: El piso de lo que puede llamarse espectro: con un solo punto no hay curva.
#: **No es el mínimo de UT-03** (eso lo aplica T-05, con su propio mensaje).
FILAS_MINIMAS: int = 2

#: Un par es «número de onda, intensidad»: dos columnas, ni una más.
COLUMNAS_CSV: int = 2

#: Los separadores que admite el `.csv`: coma o punto y coma (Requerimientos
#: §6.1; plan, sección 8, T-04). Se decide **una vez por archivo**, con la
#: primera fila: si trae punto y coma, el archivo es «de punto y coma».
SEPARADOR_CSV: str = ","
SEPARADOR_CSV_PUNTO_Y_COMA: str = ";"
SEPARADORES_CSV: tuple[str, ...] = (SEPARADOR_CSV, SEPARADOR_CSV_PUNTO_Y_COMA)

#: Con separador `;` el decimal puede venir con coma (Excel en español:
#: `400,0;0,805`). Con separador `,` el decimal es siempre punto: la coma ya
#: está ocupada.
_COMA_DECIMAL: str = ","
_PUNTO_DECIMAL: str = "."

#: Cómo se reconoce la **fila de encabezado opcional** (§6.1): es la primera
#: fila, no se lee como par de números y trae al menos una letra
#: («onda,intensidad», «cm-1;T»). Una fila sin letras que no parsea —«400.0,»—
#: no es encabezado: es una fila de datos rota.
_LETRA = re.compile(r"[^\W\d_]")

#: Los dos formatos que MOD-03 sabe revisar hoy. UT-03 decide cuáles se
#: *admiten*; esto es lo que este módulo sabe *inspeccionar*. Si UT-03 admite
#: uno que no esté aquí, el archivo se rechaza (falla cerrado) hasta que alguien
#: le enseñe la estructura: dejarlo pasar sin revisar sería peor.
EXTENSION_JDX: str = ".jdx"
EXTENSION_CSV: str = ".csv"

#: Caracteres que no pueden aparecer en un archivo de texto: controles de C0 y
#: C1 (menos tabulador, salto de línea y retorno de carro), el de borrado y el
#: carácter de reemplazo con el que MOD-02 marcó los bytes inválidos.
_NO_ES_TEXTO = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f�]")

#: Las dos etiquetas de JCAMP-DX cuya **posición** importa. La regla no se puede
#: escribir en el JSON de UT-03 (sección 3 del plan), así que vive aquí; los
#: textos siguen saliendo de la configuración.
_ETIQUETA_TITULO: str = "##TITLE="
_ETIQUETA_FIN: str = "##END="

#: Cómo empiezan las líneas que **no** son datos en un `.jdx`.
_PREFIJO_ETIQUETA: str = "##"
_PREFIJO_COMENTARIO: str = "$$"


# --------------------------------------------------------------------------- #
# Veredicto
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Veredicto:
    """Lo que MOD-03 entrega a la interfaz (contrato de la sección 5).

    Attributes:
        valido: ``True`` si el archivo pasó las cuatro capas de T-04. Ojo: que
            sea válido **aquí** no quiere decir que cumpla los requisitos de
            puntos y rango; eso lo dice T-05.
        nombre: el nombre que entregó MOD-02, ya limpio.
        extension: la extensión reconocida (``".csv"``), o ``None`` si el nombre
            no traía ninguna.
        codigo: el código de UT-02 que explica el rechazo, o ``None``.
        capa: qué capa rechazó el archivo, para el registro y las pruebas.
        detalle: una línea para el equipo sobre qué falló. **No se le muestra
            al usuario** —él ve el mensaje de UT-02— y nunca incluye contenido
            del espectro, porque va al registro (RNF-09).
    """

    valido: bool
    nombre: str
    extension: str | None
    codigo: str | None = None
    capa: str | None = None
    detalle: str = ""

    def __post_init__(self) -> None:
        # Red de seguridad contra un error de programación.
        if self.valido and (self.codigo is not None or self.capa is not None):
            raise ValueError("un veredicto válido no trae código ni capa")
        if not self.valido and (self.codigo is None or self.capa is None):
            raise ValueError("un rechazo tiene que decir su código y su capa")


@dataclass(frozen=True)
class _Fallo:
    """Resultado interno de una capa: qué falló y cómo contarlo al equipo."""

    capa: str
    detalle: str


# --------------------------------------------------------------------------- #
# Extensión
# --------------------------------------------------------------------------- #


def extension_de(nombre: str | None) -> str | None:
    """La extensión del nombre, en minúsculas y con punto.

    Devuelve ``None`` cuando no hay extensión que valga: sin punto
    (``"espectro"``), con el punto al final (``"espectro."``) o cuando el punto
    abre el nombre (``".csv"``, que es un archivo oculto sin nombre, no un
    espectro llamado «csv»).
    """
    if not nombre:
        return None
    punto = nombre.rfind(".")
    if punto <= 0 or punto == len(nombre) - 1:
        return None
    return nombre[punto:].lower()


# --------------------------------------------------------------------------- #
# Validación
# --------------------------------------------------------------------------- #


def validar(
    nombre: str,
    contenido: str,
    *,
    tamano_correcto: bool = True,
    configuracion: Configuracion | None = None,
) -> Veredicto:
    """El veredicto completo de MOD-03: formato (T-04) y requisitos (T-05).

    Args:
        nombre: el nombre que entregó MOD-02 (ya limpio).
        contenido: el archivo como texto, tal como lo entregó MOD-02.
        tamano_correcto: el indicador del contrato de la sección 5. Si viene en
            ``False`` no se revisa nada: MOD-02 no confirmó el tamaño, así que
            no hay contenido confiable que mirar.
        configuracion: los parámetros con los que se trabaja. Si es ``None`` se
            usan los de UT-03; el parámetro existe para las pruebas.

    Returns:
        El `Veredicto`. **Nunca levanta** una excepción por culpa del archivo:
        un archivo vacío, truncado o binario son resultados, no fallas
        (CA-02.4).
    """
    parametros = configuracion if configuracion is not None else obtener_configuracion()
    extension = extension_de(nombre)

    fallo = _revisar(nombre, contenido, extension, parametros, tamano_correcto)
    if fallo is None:
        fallo = _revisar_requisitos(contenido, extension, parametros)

    return _veredicto(nombre, extension, fallo)


def revisar_formato(
    nombre: str,
    contenido: str,
    *,
    tamano_correcto: bool = True,
    configuracion: Configuracion | None = None,
) -> Veredicto:
    """Solo las capas de T-04: «¿es de verdad el formato que declara?».

    No cuenta puntos ni mira el rango. Existe para probar T-04 por separado de
    T-05 (la «separación clave» del plan); la API usa `validar`.
    """
    parametros = configuracion if configuracion is not None else obtener_configuracion()
    extension = extension_de(nombre)

    fallo = _revisar(nombre, contenido, extension, parametros, tamano_correcto)

    return _veredicto(nombre, extension, fallo)


def _veredicto(nombre: str, extension: str | None, fallo: _Fallo | None) -> Veredicto:
    """Convierte el resultado de las capas en veredicto y lo deja registrado."""
    if fallo is None:
        _registro.info(
            "MOD-03 veredicto | nombre=%s | resultado=%s", nombre, "valido"
        )
        return Veredicto(valido=True, nombre=nombre, extension=extension)

    codigo = _CODIGO_POR_CAPA[fallo.capa]
    _registro.warning(
        "MOD-03 veredicto | nombre=%s | resultado=%s | capa=%s | detalle=%s",
        nombre,
        codigo,
        fallo.capa,
        fallo.detalle,
    )
    return Veredicto(
        valido=False,
        nombre=nombre,
        extension=extension,
        codigo=codigo,
        capa=fallo.capa,
        detalle=fallo.detalle,
    )


#: Qué código de UT-02 le corresponde a cada capa. Las capas 2 y 3 comparten
#: código: para el usuario, «la estructura no es la que el formato necesita»
#: cubre las dos, y el catálogo de UT-02 no se amplía sin que haga falta.
_CODIGO_POR_CAPA: dict[str, str] = {
    CAPA_TAMANO: mensajes.TAMANO_EXCEDIDO,
    CAPA_EXTENSION: mensajes.FORMATO_NO_SOPORTADO,
    CAPA_TEXTO: mensajes.ARCHIVO_NO_ES_TEXTO,
    CAPA_ESTRUCTURA: mensajes.ESTRUCTURA_INVALIDA,
    CAPA_COHERENCIA: mensajes.ESTRUCTURA_INVALIDA,
    CAPA_PUNTOS: mensajes.PUNTOS_INSUFICIENTES,
    CAPA_RANGO: mensajes.RANGO_INSUFICIENTE,
}


def _revisar(
    nombre: str,
    contenido: str,
    extension: str | None,
    parametros: Configuracion,
    tamano_correcto: bool,
) -> _Fallo | None:
    """Corre las capas en orden y devuelve la primera que falle."""
    if not tamano_correcto:
        return _Fallo(
            CAPA_TAMANO,
            "MOD-02 no confirmó el tamaño: no se revisa el contenido",
        )

    # --- Capa 0 · extensión ------------------------------------------------ #
    permitidos = parametros.archivo.formatos_permitidos
    if extension is None or extension not in permitidos:
        return _Fallo(
            CAPA_EXTENSION,
            f"la extensión no está en la lista de UT-03 ({', '.join(permitidos)})",
        )

    # --- Capa 1 · ¿es texto? ----------------------------------------------- #
    if _NO_ES_TEXTO.search(contenido) is not None:
        return _Fallo(
            CAPA_TEXTO,
            "el contenido trae bytes que no son texto imprimible",
        )

    # --- Capas 2 y 3 · estructura y coherencia del formato declarado ------- #
    if extension == EXTENSION_JDX:
        return _revisar_jdx(contenido, parametros)
    if extension == EXTENSION_CSV:
        return _revisar_csv(contenido)

    return _Fallo(
        CAPA_ESTRUCTURA,
        f"UT-03 admite «{extension}», pero MOD-03 todavía no sabe qué "
        "estructura esperar de ese formato",
    )


# --------------------------------------------------------------------------- #
# Capas 2 y 3 · CSV
# --------------------------------------------------------------------------- #


def _revisar_csv(contenido: str) -> _Fallo | None:
    """Las primeras filas tienen que ser pares «número de onda, intensidad».

    Una fila con una sola columna, con tres, con un campo vacío o con texto
    significa que el archivo no es el CSV de dos columnas que el formato pide.
    La única fila con texto que se admite es el **encabezado opcional**, y solo
    si es la primera (§6.1).
    """
    pares: list[tuple[float, float]] = []

    for fila in _filas_csv(contenido):
        if isinstance(fila, _Fallo):
            return fila
        pares.append(fila)
        if len(pares) >= FILAS_A_REVISAR:
            break

    if not pares:
        return _Fallo(CAPA_ESTRUCTURA, "el archivo no trae ni una fila de datos")

    return _coherencia(pares)


def _filas_csv(contenido: str) -> Iterator[tuple[float, float] | _Fallo]:
    """Recorre el `.csv` y entrega sus pares, o el primer fallo que encuentre.

    Es el único lugar que sabe leer una fila: T-04 se queda con las primeras y
    T-05 las recorre todas, así que las dos tareas ven el archivo igual.

    - Las líneas en blanco se saltan.
    - El separador se decide con la primera fila (encabezado incluido).
    - La primera fila puede ser un encabezado de texto, y se salta.
    - Después del primer fallo no se entrega nada más.
    """
    separador: str | None = None
    es_la_primera = True

    for linea in contenido.splitlines():
        if not linea.strip():
            continue

        if separador is None:
            separador = (
                SEPARADOR_CSV_PUNTO_Y_COMA
                if SEPARADOR_CSV_PUNTO_Y_COMA in linea
                else SEPARADOR_CSV
            )

        campos = [campo.strip() for campo in linea.split(separador)]
        par = _como_par(campos, separador)

        if par is None and es_la_primera and _LETRA.search(linea):
            es_la_primera = False
            continue  # encabezado opcional
        es_la_primera = False

        if len(campos) != COLUMNAS_CSV:
            yield _Fallo(
                CAPA_ESTRUCTURA,
                "una fila no trae dos columnas separadas por coma o punto y coma",
            )
            return
        if par is None:
            yield _Fallo(CAPA_ESTRUCTURA, "una fila no trae un par de números")
            return

        yield par


def _como_par(campos: list[str], separador: str) -> tuple[float, float] | None:
    """Los dos campos como números, o ``None`` si no lo son."""
    if len(campos) != COLUMNAS_CSV:
        return None
    if separador == SEPARADOR_CSV_PUNTO_Y_COMA:
        campos = [campo.replace(_COMA_DECIMAL, _PUNTO_DECIMAL) for campo in campos]
    try:
        return float(campos[0]), float(campos[1])
    except ValueError:
        return None


def _coherencia(pares: list[tuple[float, float]]) -> _Fallo | None:
    """Capa 3 · que haya datos suficientes y que los números sean utilizables."""
    if len(pares) < FILAS_MINIMAS:
        return _Fallo(
            CAPA_COHERENCIA,
            "con una sola fila no hay espectro que revisar",
        )

    for onda, intensidad in pares:
        if not math.isfinite(onda) or not math.isfinite(intensidad):
            return _Fallo(
                CAPA_COHERENCIA,
                "alguno de los primeros valores no es un número utilizable",
            )
        if onda <= 0:
            return _Fallo(
                CAPA_COHERENCIA,
                "alguno de los primeros números de onda no es positivo",
            )
    return None


# --------------------------------------------------------------------------- #
# Capas 2 y 3 · JCAMP-DX (.jdx)
# --------------------------------------------------------------------------- #


def _revisar_jdx(contenido: str, parametros: Configuracion) -> _Fallo | None:
    """Las etiquetas obligatorias de UT-03, sus posiciones y una de datos.

    Las líneas en blanco del final se ignoran: un editor de texto las agrega al
    guardar y eso no convierte el archivo en uno truncado.
    """
    lineas = [linea.strip() for linea in contenido.splitlines() if linea.strip()]
    if not lineas:
        return _Fallo(CAPA_ESTRUCTURA, "el archivo no trae ni una línea")

    obligatorias = parametros.validacion.jcamp_etiquetas_obligatorias
    en_mayusculas = contenido.upper()
    faltantes = [
        etiqueta for etiqueta in obligatorias if etiqueta.upper() not in en_mayusculas
    ]
    if faltantes:
        return _Fallo(
            CAPA_ESTRUCTURA,
            f"faltan etiquetas obligatorias de UT-03: {', '.join(faltantes)}",
        )

    # Las dos reglas de posición que el JSON no puede expresar. Solo se exigen
    # si UT-03 pide esas etiquetas: la configuración sigue mandando.
    if _enlistada(_ETIQUETA_TITULO, obligatorias) and not lineas[0].upper().startswith(
        _ETIQUETA_TITULO
    ):
        return _Fallo(
            CAPA_ESTRUCTURA,
            f"{_ETIQUETA_TITULO} no abre el archivo, y tiene que ir en la "
            "primera línea",
        )

    if _enlistada(_ETIQUETA_FIN, obligatorias) and not lineas[-1].upper().startswith(
        _ETIQUETA_FIN
    ):
        return _Fallo(
            CAPA_ESTRUCTURA,
            f"{_ETIQUETA_FIN} no cierra el archivo: parece cortado",
        )

    etiquetas_de_datos = parametros.validacion.jcamp_etiquetas_datos_una_de
    donde = _indice_de_datos(lineas, etiquetas_de_datos)
    if donde is None:
        return _Fallo(
            CAPA_ESTRUCTURA,
            "falta la etiqueta de datos; UT-03 admite: "
            f"{', '.join(etiquetas_de_datos)}",
        )

    datos = [
        linea
        for linea in lineas[donde + 1 :]
        if not linea.startswith(_PREFIJO_ETIQUETA)
        and not linea.startswith(_PREFIJO_COMENTARIO)
    ]
    if not datos:
        return _Fallo(
            CAPA_COHERENCIA,
            "no hay ni una línea de datos después de la etiqueta de datos",
        )

    return _primer_numero_de_onda_plausible(datos[0])


def _enlistada(etiqueta: str, etiquetas: tuple[str, ...]) -> bool:
    return any(etiqueta.upper() == otra.upper() for otra in etiquetas)


def _indice_de_datos(
    lineas: list[str], etiquetas_de_datos: tuple[str, ...]
) -> int | None:
    """En qué línea está la etiqueta que abre los datos (`##XYDATA=`, …)."""
    for indice, linea in enumerate(lineas):
        arriba = linea.upper()
        if any(arriba.startswith(etiqueta.upper()) for etiqueta in etiquetas_de_datos):
            return indice
    return None


def _primer_numero_de_onda_plausible(linea: str) -> _Fallo | None:
    """Capa 3 del `.jdx` · el primer número de onda, si se puede leer.

    A propósito es poco: JCAMP-DX permite guardar los datos comprimidos (DIF,
    SQZ), y descifrar eso es trabajo de MOD-04 en el incremento 2. Si el primer
    campo no se lee como número, se deja pasar en vez de rechazar un archivo
    por no entenderlo; si sí se lee, tiene que ser un número de onda posible.
    """
    campos = linea.replace(SEPARADOR_CSV, " ").split()
    if not campos:  # pragma: no cover - las líneas vacías ya se filtraron
        return None

    try:
        onda = float(campos[0])
    except ValueError:
        return None

    if not math.isfinite(onda) or onda <= 0:
        return _Fallo(
            CAPA_COHERENCIA,
            "el primer número de onda de los datos no es un valor posible",
        )
    return None


# --------------------------------------------------------------------------- #
# T-05 · capas 4 y 5 · puntos y rango
# --------------------------------------------------------------------------- #

#: Las tres etiquetas del encabezado JCAMP-DX que lee T-05, ya normalizadas
#: (sin `##`, sin `=`, sin espacios ni guiones, en mayúsculas). Son parte del
#: formato, no parámetros de negocio: igual que `##TITLE=` y `##END=` arriba,
#: la regla no cabe en el JSON de UT-03; los **valores** contra los que se
#: comparan (puntos mínimos y rango requerido) sí salen de UT-03.
_JDX_NPOINTS: str = "NPOINTS"
_JDX_FIRSTX: str = "FIRSTX"
_JDX_LASTX: str = "LASTX"

#: JCAMP-DX compara etiquetas sin distinguir mayúsculas y sin espacios,
#: guiones, guiones bajos ni diagonales («##N POINTS=» es «##NPOINTS=»).
_IGNORADO_EN_ETIQUETAS = re.compile(r"[\s\-_/]")


def _revisar_requisitos(
    contenido: str, extension: str | None, parametros: Configuracion
) -> _Fallo | None:
    """Capas 4 y 5. Solo se llega aquí si el formato ya pasó T-04."""
    if extension == EXTENSION_CSV:
        medida = _medir_csv(contenido)
    elif extension == EXTENSION_JDX:
        medida = _medir_jdx(contenido, parametros)
    else:  # pragma: no cover - T-04 ya rechazó cualquier otro formato
        return _Fallo(CAPA_ESTRUCTURA, "formato sin lectura de puntos y rango")

    if isinstance(medida, _Fallo):
        return medida
    return _comparar_con_ut03(*medida, parametros)


def _comparar_con_ut03(
    puntos: int, minimo: float, maximo: float, parametros: Configuracion
) -> _Fallo | None:
    """Puntos primero y rango después: un rechazo lleva un solo mensaje."""
    exigidos = parametros.validacion.puntos_minimos
    if puntos < exigidos:
        return _Fallo(
            CAPA_PUNTOS,
            f"trae {puntos} puntos y UT-03 pide al menos {exigidos}",
        )

    desde, hasta = parametros.validacion.rango_requerido_cm1
    if minimo > desde or maximo < hasta:
        return _Fallo(
            CAPA_RANGO,
            f"cubre {minimo:g}–{maximo:g} y UT-03 pide {desde:g}–{hasta:g}",
        )
    return None


def _medir_csv(contenido: str) -> tuple[int, float, float] | _Fallo:
    """Recorre **todas** las filas: cuenta pares y toma min/máx del número de onda.

    T-04 solo miró las primeras; aquí una fila rota o un valor imposible en
    cualquier parte del archivo también es rechazo.
    """
    puntos = 0
    minimo = math.inf
    maximo = -math.inf

    for fila in _filas_csv(contenido):
        if isinstance(fila, _Fallo):
            return fila
        onda, intensidad = fila
        if not math.isfinite(onda) or not math.isfinite(intensidad) or onda <= 0:
            return _Fallo(
                CAPA_COHERENCIA,
                "más adelante hay un número de onda o una intensidad que no es "
                "un valor posible",
            )
        puntos += 1
        minimo = min(minimo, onda)
        maximo = max(maximo, onda)

    return puntos, minimo, maximo


def _medir_jdx(
    contenido: str, parametros: Configuracion
) -> tuple[int, float, float] | _Fallo:
    """Lee `##NPOINTS=`, `##FIRSTX=` y `##LASTX=` del encabezado.

    Solo el encabezado: la lectura se detiene en la etiqueta de datos, y el
    bloque de datos no se descomprime. Si alguna de las tres falta o no se lee,
    **falla cerrado** (igual que T-04 con un formato que no sabe revisar).
    """
    encabezado = _encabezado_jdx(
        contenido, parametros.validacion.jcamp_etiquetas_datos_una_de
    )

    faltantes = [
        f"##{etiqueta}="
        for etiqueta in (_JDX_NPOINTS, _JDX_FIRSTX, _JDX_LASTX)
        if etiqueta not in encabezado
    ]
    if faltantes:
        return _Fallo(
            CAPA_ESTRUCTURA,
            f"el encabezado no trae {', '.join(faltantes)}: sin eso no se pueden "
            "revisar puntos y rango",
        )

    try:
        puntos_leidos = float(encabezado[_JDX_NPOINTS])
        primero = float(encabezado[_JDX_FIRSTX])
        ultimo = float(encabezado[_JDX_LASTX])
    except ValueError:
        return _Fallo(
            CAPA_ESTRUCTURA,
            "##NPOINTS=, ##FIRSTX= o ##LASTX= no traen un número",
        )

    if (
        not all(math.isfinite(valor) for valor in (puntos_leidos, primero, ultimo))
        or puntos_leidos <= 0
        or puntos_leidos != int(puntos_leidos)
    ):
        return _Fallo(
            CAPA_ESTRUCTURA,
            "##NPOINTS=, ##FIRSTX= o ##LASTX= traen un valor imposible",
        )

    # El eje puede ir de mayor a menor (4000 → 400): se usan mínimo y máximo.
    return int(puntos_leidos), min(primero, ultimo), max(primero, ultimo)


def _encabezado_jdx(
    contenido: str, etiquetas_de_datos: tuple[str, ...]
) -> dict[str, str]:
    """Las etiquetas del encabezado, normalizadas, con su valor sin comentarios.

    Si una etiqueta se repite, vale la primera.
    """
    datos = tuple(etiqueta.upper() for etiqueta in etiquetas_de_datos)
    encabezado: dict[str, str] = {}

    for linea in contenido.splitlines():
        limpia = linea.strip()
        if not limpia.startswith(_PREFIJO_ETIQUETA):
            continue
        if limpia.upper().startswith(datos):
            break
        etiqueta, igual, valor = limpia[len(_PREFIJO_ETIQUETA) :].partition("=")
        if not igual:
            continue
        normal = _IGNORADO_EN_ETIQUETAS.sub("", etiqueta).upper()
        sin_comentario = valor.split(_PREFIJO_COMENTARIO, 1)[0].strip()
        encabezado.setdefault(normal, sin_comentario)

    return encabezado
