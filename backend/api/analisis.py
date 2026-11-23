"""Ruta del análisis: MOD-01 pide, MOD-06 identifica (incremento 3).

POST /api/analizar recibe en JSON el eje y la intensidad que MOD-04 entregó al
validar el archivo. Nunca recibe el archivo: así MOD-06 queda aislado, como
pide su diseño, y el servidor no tiene que guardar nada entre una petición y
otra (RNF-09).

La respuesta trae las detecciones del motor ordenadas de mayor a menor
confianza, cada una con el nombre del grupo que sale de UT-01 y su porcentaje.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.nucleo import obtener_registro
from backend.utilerias import mensajes
from backend.utilerias.catalogo import Catalogo
from backend.utilerias.configuracion import Configuracion
from motor_identificacion.motor import identificar

_registro = obtener_registro("api")

RUTA_ANALIZAR: str = "/api/analizar"


class PeticionInvalida(Exception):
    """El cuerpo no trae un eje y una intensidad que el motor pueda usar."""


def registrar(
    aplicacion: FastAPI, parametros: Configuracion, catalogo: Catalogo
) -> None:
    @aplicacion.post(RUTA_ANALIZAR)
    async def analizar(peticion: Request) -> JSONResponse:
        # T-19: cualquier falla, sea del cuerpo o del motor, termina en el
        # mismo mensaje de UT-02, sin detalles técnicos. El registro guarda
        # solo el tipo de error, nunca los valores del espectro.
        try:
            eje, intensidad = _leer_cuerpo(await peticion.json(), parametros)
        except Exception as error:
            _registro.warning(
                "api analisis rechazado | tipo=%s", type(error).__name__
            )
            return respuesta_de_error(mensajes.ANALISIS_FALLIDO, parametros, 400)
        try:
            resultado = analizar_espectro(eje, intensidad, parametros, catalogo)
        except Exception as error:
            _registro.error("api analisis fallo del motor | tipo=%s", type(error).__name__)
            return respuesta_de_error(mensajes.ANALISIS_FALLIDO, parametros, 500)
        return JSONResponse(resultado)


def analizar_espectro(
    eje: list[float],
    intensidad: list[float],
    parametros: Configuracion,
    catalogo: Catalogo,
) -> dict[str, Any]:
    motor = parametros.motor
    resultado = identificar(
        eje,
        intensidad,
        catalogo.grupos,
        umbral=motor.umbral_confianza,
        peso_reglas=motor.peso_reglas,
        peso_ml=motor.peso_ml,
    )
    for deteccion in resultado["detecciones"]:
        grupo = catalogo.grupo(deteccion["grupo"])
        deteccion["nombre"] = grupo.nombre
        deteccion["familias"] = grupo.familias
        deteccion["porcentaje"] = porcentaje(deteccion["confianza"])
    if resultado["sin_detecciones"]:
        aviso = mensajes.obtener(mensajes.SIN_DETECCIONES, parametros)
        resultado["aviso"] = {
            "titulo": aviso.titulo,
            "mensaje": aviso.texto,
            "accion": aviso.accion,
        }
    _registro.info(
        "MOD-06 analisis | detecciones=%s",
        ",".join(d["grupo"] for d in resultado["detecciones"]) or "ninguna",
    )
    return resultado


def porcentaje(confianza: float) -> float:
    """La confianza en por ciento, con un decimal solo si hace falta."""
    valor = round(confianza * 100, 1)
    return int(valor) if valor == int(valor) else valor


def _leer_cuerpo(cuerpo: Any, parametros: Configuracion) -> tuple[list[float], list[float]]:
    if not isinstance(cuerpo, dict):
        raise PeticionInvalida("el cuerpo no es un objeto")
    eje, intensidad = cuerpo.get("eje_cm1"), cuerpo.get("intensidad")
    esperados = parametros.procesamiento.puntos_rejilla
    for lista in (eje, intensidad):
        if not isinstance(lista, list) or len(lista) != esperados:
            raise PeticionInvalida("el vector no tiene el tamaño de la rejilla")
        for valor in lista:
            if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                raise PeticionInvalida("el vector trae algo que no es un número")
            if not math.isfinite(valor):
                raise PeticionInvalida("el vector trae un número imposible")
    return [float(v) for v in eje], [float(v) for v in intensidad]


def respuesta_de_error(codigo: str, parametros: Configuracion, estado: int) -> JSONResponse:
    mensaje = mensajes.obtener(codigo, parametros)
    return JSONResponse(
        {"titulo": mensaje.titulo, "mensaje": mensaje.texto, "accion": mensaje.accion},
        status_code=estado,
    )
