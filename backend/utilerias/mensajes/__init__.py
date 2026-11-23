"""UT-02 · Errores y mensajes.

Uso habitual:

    from backend.utilerias import mensajes

    mensaje = mensajes.obtener(mensajes.FORMATO_NO_SOPORTADO)
    mensaje.titulo, mensaje.texto, mensaje.accion
"""

from backend.utilerias.mensajes.catalogo import (
    ARCHIVO_NO_ES_TEXTO,
    ARCHIVO_NO_RECIBIDO,
    CONFIGURACION_INCOMPLETA,
    DATOS_ILEGIBLES,
    ERROR_INTERNO,
    ESTRUCTURA_INVALIDA,
    FORMATO_NO_SOPORTADO,
    LECTURA_INTERRUMPIDA,
    PUNTOS_INSUFICIENTES,
    RANGO_INSUFICIENTE,
    TAMANO_EXCEDIDO,
    CodigoDesconocido,
    Mensaje,
    codigos,
    obtener,
)

__all__ = [
    "ARCHIVO_NO_ES_TEXTO",
    "ARCHIVO_NO_RECIBIDO",
    "CONFIGURACION_INCOMPLETA",
    "DATOS_ILEGIBLES",
    "ERROR_INTERNO",
    "ESTRUCTURA_INVALIDA",
    "FORMATO_NO_SOPORTADO",
    "LECTURA_INTERRUMPIDA",
    "PUNTOS_INSUFICIENTES",
    "RANGO_INSUFICIENTE",
    "TAMANO_EXCEDIDO",
    "CodigoDesconocido",
    "Mensaje",
    "codigos",
    "obtener",
]
