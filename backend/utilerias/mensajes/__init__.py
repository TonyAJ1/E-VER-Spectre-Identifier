"""UT-02 · Errores y mensajes.

Uso habitual:

    from backend.utilerias import mensajes

    mensaje = mensajes.obtener(mensajes.FORMATO_NO_SOPORTADO)
    mensaje.titulo, mensaje.texto, mensaje.accion
"""

from backend.utilerias.mensajes.catalogo import (
    ANALISIS_FALLIDO,
    ARCHIVO_NO_ES_TEXTO,
    ARCHIVO_NO_RECIBIDO,
    CONFIGURACION_INCOMPLETA,
    DATOS_ILEGIBLES,
    ERROR_INTERNO,
    ESTRUCTURA_INVALIDA,
    EXPLICACION_NO_DISPONIBLE,
    FORMATO_NO_SOPORTADO,
    LECTURA_INTERRUMPIDA,
    PUNTOS_INSUFICIENTES,
    RANGO_INSUFICIENTE,
    REPORTE_FALLIDO,
    RESULTADO_ORIENTATIVO,
    SIN_DETECCIONES,
    SIN_SENAL,
    TAMANO_EXCEDIDO,
    CodigoDesconocido,
    Mensaje,
    codigos,
    obtener,
)

__all__ = [
    "ANALISIS_FALLIDO",
    "ARCHIVO_NO_ES_TEXTO",
    "ARCHIVO_NO_RECIBIDO",
    "CONFIGURACION_INCOMPLETA",
    "DATOS_ILEGIBLES",
    "ERROR_INTERNO",
    "ESTRUCTURA_INVALIDA",
    "EXPLICACION_NO_DISPONIBLE",
    "FORMATO_NO_SOPORTADO",
    "LECTURA_INTERRUMPIDA",
    "PUNTOS_INSUFICIENTES",
    "RANGO_INSUFICIENTE",
    "REPORTE_FALLIDO",
    "RESULTADO_ORIENTATIVO",
    "SIN_DETECCIONES",
    "SIN_SENAL",
    "TAMANO_EXCEDIDO",
    "CodigoDesconocido",
    "Mensaje",
    "codigos",
    "obtener",
]
