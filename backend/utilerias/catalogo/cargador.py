"""UT-01, catálogo de los 7 grupos funcionales (tarea T-14).

Lee datos/catalogo/grupos.json una sola vez y lo entrega como objetos que no
se pueden modificar. Es la única fuente de regiones y rasgos: el motor, la
capa educativa, la gráfica y el reporte le piden los datos a este módulo en
lugar de abrir el archivo por su cuenta (diseño de persistencia, sin base de
datos).

Si el archivo falta o le falta algo a un grupo, se levanta ErrorDeCatalogo y
la aplicación no arranca. Un catálogo incompleto daría resultados equivocados
sin avisar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[3]
CARPETA_CATALOGO = RAIZ / "datos" / "catalogo"
RUTA_GRUPOS = CARPETA_CATALOGO / "grupos.json"
RUTA_PLANTILLAS = CARPETA_CATALOGO / "plantillas.json"

#: La lista cerrada de Requerimientos V3: siete grupos, ni uno más ni uno menos.
IDS_ESPERADOS = ("GF-01", "GF-02", "GF-03", "GF-04", "GF-05", "GF-06", "GF-07")


class ErrorDeCatalogo(Exception):
    """El catálogo falta, no se puede leer o está incompleto."""


@dataclass(frozen=True)
class RegionAlterna:
    nombre: str
    region_cm1: tuple[float, float]


@dataclass(frozen=True)
class Acompanante:
    """Una segunda banda que tiene que aparecer junto a la principal."""

    nombre: str
    region_cm1: tuple[float, float]
    prominencia_referencia: float


@dataclass(frozen=True)
class Regla:
    """Lo que la vía de reglas de MOD-06 necesita saber de un grupo."""

    prominencia_referencia: float
    ancho_minimo_cm1: float | None = None
    ancho_maximo_cm1: float | None = None
    acompanante: Acompanante | None = None


@dataclass(frozen=True)
class Grupo:
    id: str
    nombre: str
    familias: str
    enlace: str
    region_cm1: tuple[float, float]
    regiones_alternas: tuple[RegionAlterna, ...]
    intensidad: str
    forma: str
    rasgo: str
    regla: Regla

    def regiones_de_busqueda(self) -> tuple[tuple[float, float], ...]:
        """La región principal y las alternas, donde se busca el pico."""
        return (self.region_cm1,) + tuple(r.region_cm1 for r in self.regiones_alternas)


@dataclass(frozen=True)
class Catalogo:
    grupos: tuple[Grupo, ...]

    def grupo(self, identificador: str) -> Grupo | None:
        for grupo in self.grupos:
            if grupo.id == identificador:
                return grupo
        return None


def _error(detalle: str, ruta: Path) -> ErrorDeCatalogo:
    return ErrorDeCatalogo(f"UT-01: {detalle} (archivo: {ruta})")


def _texto(datos: dict[str, Any], llave: str, donde: str, ruta: Path) -> str:
    valor = datos.get(llave)
    if not isinstance(valor, str) or not valor.strip():
        raise _error(f"a {donde} le falta el texto «{llave}»", ruta)
    return valor.strip()


def _positivo(datos: dict[str, Any], llave: str, donde: str, ruta: Path) -> float:
    valor = datos.get(llave)
    if isinstance(valor, bool) or not isinstance(valor, (int, float)) or valor <= 0:
        raise _error(f"en {donde}, «{llave}» tiene que ser un número mayor que cero", ruta)
    return float(valor)


def _opcional(datos: dict[str, Any], llave: str, donde: str, ruta: Path) -> float | None:
    if llave not in datos:
        return None
    return _positivo(datos, llave, donde, ruta)


def _region(valor: Any, donde: str, ruta: Path) -> tuple[float, float]:
    if (
        not isinstance(valor, list)
        or len(valor) != 2
        or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in valor)
        or not 0 < valor[0] < valor[1]
    ):
        raise _error(f"la región de {donde} tiene que ser [menor, mayor] en cm⁻¹", ruta)
    return float(valor[0]), float(valor[1])


def _grupo(datos: Any, ruta: Path) -> Grupo:
    if not isinstance(datos, dict):
        raise _error("cada grupo tiene que ser un objeto", ruta)
    identificador = _texto(datos, "id", "un grupo", ruta)
    donde = f"el grupo {identificador}"

    alternas = []
    for alterna in datos.get("regiones_alternas", []):
        if not isinstance(alterna, dict):
            raise _error(f"una región alterna de {donde} no es un objeto", ruta)
        alternas.append(
            RegionAlterna(
                nombre=_texto(alterna, "nombre", donde, ruta),
                region_cm1=_region(alterna.get("region_cm1"), donde, ruta),
            )
        )

    regla_datos = datos.get("regla")
    if not isinstance(regla_datos, dict):
        raise _error(f"a {donde} le falta el bloque «regla»", ruta)
    acompanante = None
    if "acompanante" in regla_datos:
        bloque = regla_datos["acompanante"]
        if not isinstance(bloque, dict):
            raise _error(f"el acompañante de {donde} no es un objeto", ruta)
        acompanante = Acompanante(
            nombre=_texto(bloque, "nombre", donde, ruta),
            region_cm1=_region(bloque.get("region_cm1"), donde, ruta),
            prominencia_referencia=_positivo(bloque, "prominencia_referencia", donde, ruta),
        )

    return Grupo(
        id=identificador,
        nombre=_texto(datos, "nombre", donde, ruta),
        familias=_texto(datos, "familias", donde, ruta),
        enlace=_texto(datos, "enlace", donde, ruta),
        region_cm1=_region(datos.get("region_cm1"), donde, ruta),
        regiones_alternas=tuple(alternas),
        intensidad=_texto(datos, "intensidad", donde, ruta),
        forma=_texto(datos, "forma", donde, ruta),
        rasgo=_texto(datos, "rasgo", donde, ruta),
        regla=Regla(
            prominencia_referencia=_positivo(
                regla_datos, "prominencia_referencia", donde, ruta
            ),
            ancho_minimo_cm1=_opcional(regla_datos, "ancho_minimo_cm1", donde, ruta),
            ancho_maximo_cm1=_opcional(regla_datos, "ancho_maximo_cm1", donde, ruta),
            acompanante=acompanante,
        ),
    )


def cargar(ruta: Path | str | None = None) -> Catalogo:
    """Lee y revisa el catálogo. Levanta ErrorDeCatalogo si algo falta."""
    ruta_final = Path(ruta) if ruta is not None else RUTA_GRUPOS
    if not ruta_final.is_file():
        raise _error("no se encontró el catálogo", ruta_final)
    try:
        datos = json.loads(ruta_final.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise _error("el catálogo no se pudo leer como JSON", ruta_final) from error

    lista = datos.get("grupos") if isinstance(datos, dict) else None
    if not isinstance(lista, list):
        raise _error("falta la lista «grupos»", ruta_final)
    grupos = tuple(_grupo(grupo, ruta_final) for grupo in lista)

    ids = tuple(grupo.id for grupo in grupos)
    if tuple(sorted(ids)) != IDS_ESPERADOS:
        raise _error(
            f"el catálogo tiene que traer exactamente {', '.join(IDS_ESPERADOS)}",
            ruta_final,
        )
    return Catalogo(grupos=tuple(sorted(grupos, key=lambda g: g.id)))


_catalogo: Catalogo | None = None


def obtener() -> Catalogo:
    """El catálogo, leído la primera vez y guardado en memoria."""
    global _catalogo
    if _catalogo is None:
        _catalogo = cargar()
    return _catalogo


# Plantillas de explicación (tarea T-20)
#
# Viven aparte del catálogo para que un grupo sin plantilla no impida
# arrancar: ese caso lo cubre MOD-07 con «Explicación no disponible» (T-22).
# Lo que sí impide arrancar es un archivo roto o una plantilla de un grupo que
# no existe.


@dataclass(frozen=True)
class Plantilla:
    grupo: str
    por_que: str
    fuentes: tuple[str, ...]
    revisado_por: str | None


def cargar_plantillas(ruta: Path | str | None = None) -> dict[str, Plantilla]:
    ruta_final = Path(ruta) if ruta is not None else RUTA_PLANTILLAS
    if not ruta_final.is_file():
        raise _error("no se encontraron las plantillas de explicación", ruta_final)
    try:
        datos = json.loads(ruta_final.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise _error("las plantillas no se pudieron leer como JSON", ruta_final) from error

    lista = datos.get("plantillas") if isinstance(datos, dict) else None
    if not isinstance(lista, list):
        raise _error("falta la lista «plantillas»", ruta_final)

    plantillas: dict[str, Plantilla] = {}
    for entrada in lista:
        if not isinstance(entrada, dict):
            raise _error("cada plantilla tiene que ser un objeto", ruta_final)
        grupo = _texto(entrada, "grupo", "una plantilla", ruta_final)
        if grupo not in IDS_ESPERADOS:
            raise _error(f"hay una plantilla para {grupo}, que no está en el catálogo", ruta_final)
        if grupo in plantillas:
            raise _error(f"el grupo {grupo} tiene dos plantillas", ruta_final)
        fuentes = entrada.get("fuentes", [])
        revisor = entrada.get("revisado_por")
        plantillas[grupo] = Plantilla(
            grupo=grupo,
            por_que=_texto(entrada, "por_que", f"la plantilla de {grupo}", ruta_final),
            fuentes=tuple(f for f in fuentes if isinstance(f, str)),
            revisado_por=revisor if isinstance(revisor, str) and revisor.strip() else None,
        )
    return plantillas


_plantillas: dict[str, Plantilla] | None = None


def obtener_plantillas() -> dict[str, Plantilla]:
    """Las plantillas, leídas la primera vez y guardadas en memoria."""
    global _plantillas
    if _plantillas is None:
        _plantillas = cargar_plantillas()
    return _plantillas
