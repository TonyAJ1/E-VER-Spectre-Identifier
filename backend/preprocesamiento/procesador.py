"""Punto de entrada de MOD-04.

Une los pasos en el orden del plan: leer (T-08), ordenar y pasar a absorbancia
(T-09), y acomodar en la rejilla fija con intensidad entre 0 y 1 (T-10).

Igual que MOD-03, esta función no levanta excepciones por culpa del archivo.
Si algo sale mal devuelve un resultado no válido con su código de UT-02, y el
registro solo guarda el nombre y el motivo, nunca los valores del espectro.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.nucleo import obtener_registro
from backend.preprocesamiento import conversion, rejilla
from backend.preprocesamiento.lector import ArchivoIlegible, leer
from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion

_registro = obtener_registro("mod-04")


@dataclass(frozen=True)
class EspectroProcesado:
    """Lo que MOD-04 entrega a MOD-05 y a MOD-06.

    eje_cm1 va de mayor a menor número de onda. intensidad trae un valor por
    cada punto del eje, entre 0 y 1. rango_medido_cm1 es el tramo que de verdad
    midió el archivo. unidad_original dice en qué venía la intensidad.
    """

    eje_cm1: tuple[float, ...]
    intensidad: tuple[float, ...]
    rango_medido_cm1: tuple[float, float]
    unidad_original: str


@dataclass(frozen=True)
class Resultado:
    valido: bool
    espectro: EspectroProcesado | None = None
    codigo: str | None = None
    detalle: str = ""


def procesar(
    nombre: str, contenido: str, configuracion: Configuracion | None = None
) -> Resultado:
    """Procesa el texto de un archivo que MOD-03 ya aprobó."""
    parametros = configuracion if configuracion is not None else obtener_configuracion()

    try:
        lectura = leer(nombre, contenido)
    except ArchivoIlegible as error:
        return _rechazo(nombre, mensajes.DATOS_ILEGIBLES, str(error))

    ordenados = conversion.ordenar(lectura.pares)
    intensidades = [intensidad for _, intensidad in ordenados]
    unidad = conversion.unidad_efectiva(intensidades, lectura.unidad)
    absorbancias = conversion.a_absorbancia(intensidades, lectura.unidad)
    en_absorbancia = [
        (onda, absorbancia)
        for (onda, _), absorbancia in zip(ordenados, absorbancias)
    ]

    procesamiento = parametros.procesamiento
    eje = rejilla.eje(procesamiento.puntos_rejilla, procesamiento.rango_rejilla_cm1)
    valores, medido = rejilla.remuestrear(en_absorbancia, eje)
    if all(valor is None for valor in valores):
        return _rechazo(
            nombre, mensajes.DATOS_ILEGIBLES, "el espectro no toca la rejilla"
        )

    espectro = EspectroProcesado(
        eje_cm1=tuple(eje),
        intensidad=tuple(rejilla.normalizar(valores)),
        rango_medido_cm1=medido,
        unidad_original=unidad,
    )
    _registro.info("MOD-04 procesado | nombre=%s | unidad=%s", nombre, unidad)
    return Resultado(valido=True, espectro=espectro)


def _rechazo(nombre: str, codigo: str, detalle: str) -> Resultado:
    _registro.warning(
        "MOD-04 rechazo | nombre=%s | codigo=%s | detalle=%s", nombre, codigo, detalle
    )
    return Resultado(valido=False, codigo=codigo, detalle=detalle)
