"""Reporte PDF del análisis (tarea T-25).

Arma el PDF con reportlab, la librería elegida en la decisión D-3, y lo arma
completo en memoria: se escribe en un BytesIO y se devuelve como bytes, sin
tocar el disco (RNF-09). El servidor no guarda el reporte; la página lo
descarga y ahí termina.

El reporte lleva lo que pide RF-08: el nombre del archivo, la fecha y hora del
análisis, la gráfica con las regiones resaltadas (desde T-26), cada grupo con
su confianza y su explicación y el aviso de que el resultado es orientativo. Los textos de los grupos salen del catálogo y de
MOD-07, no de lo que mande la página.

Para que se vean bien símbolos como C≡N o cm⁻¹ se usa la fuente DejaVu, que
viene en backend/reportes/fuentes con su licencia libre.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

CARPETA_FUENTES = Path(__file__).resolve().parent / "fuentes"
FUENTE = "DejaVuSans"
FUENTE_NEGRITA = "DejaVuSans-Bold"

TITULO = "Reporte de análisis infrarrojo"
NOMBRE_DESCARGA = "reporte_analisis.pdf"

_fuentes_listas = False


def _registrar_fuentes() -> None:
    global _fuentes_listas
    if _fuentes_listas:
        return
    pdfmetrics.registerFont(TTFont(FUENTE, str(CARPETA_FUENTES / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(
        TTFont(FUENTE_NEGRITA, str(CARPETA_FUENTES / "DejaVuSans-Bold.ttf"))
    )
    # Para que la marca de negritas del texto use la versión negrita.
    pdfmetrics.registerFontFamily(
        FUENTE, normal=FUENTE, bold=FUENTE_NEGRITA, italic=FUENTE, boldItalic=FUENTE_NEGRITA
    )
    _fuentes_listas = True


@dataclass(frozen=True)
class GrupoDelReporte:
    nombre: str
    familias: str
    porcentaje: float
    explicacion: dict


@dataclass(frozen=True)
class DatosDelReporte:
    nombre_archivo: str
    fecha_hora: datetime
    grupos: list[GrupoDelReporte]
    aviso_orientativo: str
    sin_detecciones: str | None = None
    imagen_png: bytes | None = field(default=None, repr=False)


def _estilos() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName=FUENTE, fontSize=10, leading=14)
    return {
        "titulo": ParagraphStyle("titulo", parent=base, fontName=FUENTE_NEGRITA, fontSize=18, leading=22, spaceAfter=6),
        "subtitulo": ParagraphStyle("subtitulo", parent=base, fontName=FUENTE_NEGRITA, fontSize=13, leading=17, spaceBefore=10, spaceAfter=4),
        "grupo": ParagraphStyle("grupo", parent=base, fontName=FUENTE_NEGRITA, fontSize=11, leading=15, spaceBefore=8),
        "texto": base,
        "suave": ParagraphStyle("suave", parent=base, textColor=colors.HexColor("#556070")),
        "aviso": ParagraphStyle("aviso", parent=base, textColor=colors.HexColor("#7a4b00"), spaceBefore=12),
    }


def _escapar(texto: str) -> str:
    """Paragraph de reportlab entiende un poco de marcado; el texto se escapa
    para que un nombre de archivo raro no rompa el PDF."""
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _porcentaje(valor: float) -> str:
    texto = f"{valor:g}".replace(".", ",")
    return f"{texto} %"


def generar_pdf(datos: DatosDelReporte) -> bytes:
    """Devuelve el PDF del reporte como bytes."""
    _registrar_fuentes()
    estilos = _estilos()
    salida = BytesIO()
    documento = SimpleDocTemplate(
        salida,
        pagesize=letter,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=TITULO,
        author="E-VER Spectre Identifier",
    )

    partes = [
        Paragraph(TITULO, estilos["titulo"]),
        Paragraph(f"Archivo: {_escapar(datos.nombre_archivo)}", estilos["texto"]),
        Paragraph(
            f"Fecha y hora del análisis: {datos.fecha_hora.strftime('%d/%m/%Y %H:%M')}",
            estilos["texto"],
        ),
    ]
    partes += _seccion_grafica(datos, estilos)
    partes.append(Paragraph("Grupos funcionales detectados", estilos["subtitulo"]))
    if datos.sin_detecciones:
        partes.append(Paragraph(_escapar(datos.sin_detecciones), estilos["texto"]))
    else:
        partes += _seccion_grupos(datos, estilos)
    partes.append(Paragraph(_escapar(datos.aviso_orientativo), estilos["aviso"]))

    documento.build(partes)
    return salida.getvalue()


#: Ancho de la gráfica en la hoja. El alto sale de la proporción de la imagen.
ANCHO_GRAFICA = 17 * cm


def _seccion_grafica(datos: DatosDelReporte, estilos) -> list:
    """T-26: la gráfica con las regiones resaltadas, tal como la dibujó la
    página. Si por alguna razón no llegó, el reporte lo dice en lugar de dejar
    un hueco."""
    partes: list = [Paragraph("Espectro con las regiones resaltadas", estilos["subtitulo"])]
    if not datos.imagen_png:
        partes.append(Paragraph("No se recibió la imagen de la gráfica.", estilos["suave"]))
        return partes
    lector = ImageReader(BytesIO(datos.imagen_png))
    ancho, alto = lector.getSize()
    partes.append(
        Image(BytesIO(datos.imagen_png), width=ANCHO_GRAFICA, height=ANCHO_GRAFICA * alto / ancho)
    )
    return partes


def _seccion_grupos(datos: DatosDelReporte, estilos) -> list:
    partes: list = []
    for grupo in datos.grupos:
        partes.append(
            Paragraph(
                f"{_escapar(grupo.nombre)}: {_porcentaje(grupo.porcentaje)} de confianza",
                estilos["grupo"],
            )
        )
        partes.append(Paragraph(_escapar(grupo.familias), estilos["suave"]))
        explicacion = grupo.explicacion
        if not explicacion.get("disponible"):
            partes.append(Paragraph(_escapar(explicacion.get("aviso", "")), estilos["suave"]))
            continue
        posicion = explicacion.get("posicion") or "sin posición exacta del pico"
        for etiqueta, valor in (
            ("Región característica", explicacion["region"]),
            ("Pico observado", posicion),
            ("Lo que lo delata", explicacion["rasgo"]),
            ("Por qué corresponde a este grupo", explicacion["por_que"]),
        ):
            partes.append(
                Paragraph(f"<b>{etiqueta}:</b> {_escapar(valor)}", estilos["texto"])
            )
        partes.append(Spacer(1, 4))
    return partes
