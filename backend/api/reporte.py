"""Ruta del reporte: la página pide el PDF y MOD-08 lo arma (incremento 5).

POST /api/reporte recibe en JSON el nombre del archivo, la fecha y hora del
análisis y las detecciones que mostró la página. El servidor no guardó nada
del análisis (RNF-09), así que la página le manda lo necesario. Lo que no se
toma de la página son los textos: los nombres, las regiones y las
explicaciones se vuelven a armar con el catálogo de UT-01 y con MOD-07, para
que el PDF diga lo mismo que dice el sistema.

La respuesta es el PDF como descarga. No se escribe en disco.
"""

from __future__ import annotations

import base64
import binascii
import math
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import Response

from backend.api.analisis import porcentaje
from backend.educativo.explicador import explicar
from backend.nucleo import obtener_registro
from backend.reportes.generador import (
    NOMBRE_DESCARGA,
    DatosDelReporte,
    GrupoDelReporte,
    generar_pdf,
)
from backend.utilerias import mensajes
from backend.utilerias.catalogo import Catalogo, obtener_plantillas
from backend.utilerias.configuracion import Configuracion

_registro = obtener_registro("api")

RUTA_REPORTE: str = "/api/reporte"

#: Tope de la imagen de la gráfica, ya decodificada. Una gráfica de la
#: página pesa unos cientos de kilobytes; el tope solo evita cuerpos absurdos.
BYTES_MAXIMOS_IMAGEN = 4 * 1024 * 1024

_PREFIJO_PNG = "data:image/png;base64,"
_FIRMA_PNG = b"\x89PNG\r\n\x1a\n"

#: Largo máximo del nombre que se imprime en el reporte. Es solo una defensa
#: contra cuerpos absurdos, no un parámetro de negocio.
LARGO_MAXIMO_NOMBRE = 255


class PeticionInvalida(Exception):
    """El cuerpo no trae lo necesario para armar el reporte."""


def registrar(
    aplicacion: FastAPI, parametros: Configuracion, catalogo: Catalogo
) -> None:
    @aplicacion.post(RUTA_REPORTE)
    async def reporte(peticion: Request) -> Response:
        datos = armar_datos(await peticion.json(), parametros, catalogo)
        pdf = generar_pdf(datos)
        _registro.info(
            "MOD-08 reporte | nombre=%s | grupos=%d | bytes=%d",
            datos.nombre_archivo,
            len(datos.grupos),
            len(pdf),
        )
        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{NOMBRE_DESCARGA}"',
                "Cache-Control": "no-store",
            },
        )


def armar_datos(
    cuerpo: Any, parametros: Configuracion, catalogo: Catalogo
) -> DatosDelReporte:
    if not isinstance(cuerpo, dict):
        raise PeticionInvalida("el cuerpo no es un objeto")

    nombre = cuerpo.get("nombre_archivo")
    if not isinstance(nombre, str) or not nombre.strip() or len(nombre) > LARGO_MAXIMO_NOMBRE:
        raise PeticionInvalida("falta el nombre del archivo")
    try:
        fecha_hora = datetime.fromisoformat(str(cuerpo.get("fecha_hora")))
    except ValueError as error:
        raise PeticionInvalida("la fecha y hora no se pudo leer") from error

    detecciones = cuerpo.get("detecciones")
    if not isinstance(detecciones, list):
        raise PeticionInvalida("faltan las detecciones")

    plantillas = obtener_plantillas()
    grupos = []
    for entrada in detecciones:
        deteccion = _deteccion(entrada, catalogo)
        datos_grupo = catalogo.grupo(deteccion["grupo"])
        grupos.append(
            GrupoDelReporte(
                nombre=datos_grupo.nombre,
                familias=datos_grupo.familias,
                porcentaje=porcentaje(deteccion["confianza"]),
                explicacion=explicar(deteccion, catalogo, plantillas),
            )
        )
    grupos.sort(key=lambda g: -g.porcentaje)

    return DatosDelReporte(
        nombre_archivo=nombre.strip(),
        fecha_hora=fecha_hora,
        grupos=grupos,
        aviso_orientativo=mensajes.obtener(mensajes.RESULTADO_ORIENTATIVO, parametros).texto,
        imagen_png=_imagen(cuerpo.get("imagen_png")),
    )


def _imagen(valor: Any) -> bytes | None:
    """La gráfica que manda la página, como PNG. Solo se acepta un PNG de
    verdad; cualquier otra cosa se rechaza sin intentar abrirla."""
    if valor is None:
        return None
    if not isinstance(valor, str) or not valor.startswith(_PREFIJO_PNG):
        raise PeticionInvalida("la gráfica no viene como PNG")
    texto = valor[len(_PREFIJO_PNG):]
    if len(texto) > BYTES_MAXIMOS_IMAGEN * 4 // 3 + 4:
        raise PeticionInvalida("la gráfica es demasiado grande")
    try:
        datos = base64.b64decode(texto, validate=True)
    except (binascii.Error, ValueError) as error:
        raise PeticionInvalida("la gráfica no se pudo leer") from error
    if not datos.startswith(_FIRMA_PNG):
        raise PeticionInvalida("la gráfica no es un PNG")
    return datos


def _deteccion(entrada: Any, catalogo: Catalogo) -> dict[str, Any]:
    if not isinstance(entrada, dict):
        raise PeticionInvalida("una detección no es un objeto")
    grupo = catalogo.grupo(str(entrada.get("grupo")))
    if grupo is None:
        raise PeticionInvalida("una detección no es de un grupo del catálogo")

    confianza = entrada.get("confianza")
    if (
        isinstance(confianza, bool)
        or not isinstance(confianza, (int, float))
        or not 0 <= confianza <= 1
    ):
        raise PeticionInvalida("una confianza no está entre 0 y 1")

    pico = entrada.get("pico_cm1")
    if pico is not None and (
        isinstance(pico, bool) or not isinstance(pico, (int, float)) or not math.isfinite(pico)
    ):
        raise PeticionInvalida("la posición de un pico no es un número")

    # La región tiene que ser una de las del catálogo para ese grupo; si no,
    # se usa la principal.
    region = entrada.get("region_cm1")
    regiones = [list(r) for r in grupo.regiones_de_busqueda()]
    if not isinstance(region, list) or [float(v) for v in region if isinstance(v, (int, float))] not in regiones:
        region = list(grupo.region_cm1)

    return {
        "grupo": grupo.id,
        "confianza": float(confianza),
        "region_cm1": [float(v) for v in region],
        "pico_cm1": None if pico is None else float(pico),
    }
