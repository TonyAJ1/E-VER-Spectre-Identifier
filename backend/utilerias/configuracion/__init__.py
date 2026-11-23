"""UT-03 · Configuración.

Única fuente operativa de los parámetros. Uso habitual:

    from backend.utilerias.configuracion import obtener as obtener_configuracion

    configuracion = obtener_configuracion()
    configuracion.archivo.tamano_maximo_bytes
"""

from backend.utilerias.configuracion.cargador import (
    CARPETA,
    NOMBRE_ARCHIVO,
    PATRON_ARCHIVO,
    RUTA_PARAMETROS,
    Configuracion,
    ErrorDeConfiguracion,
    ParametrosArchivo,
    ParametrosProcesamiento,
    ParametrosValidacion,
    cargar,
    obtener,
    recargar,
)

__all__ = [
    "CARPETA",
    "NOMBRE_ARCHIVO",
    "PATRON_ARCHIVO",
    "RUTA_PARAMETROS",
    "Configuracion",
    "ErrorDeConfiguracion",
    "ParametrosArchivo",
    "ParametrosProcesamiento",
    "ParametrosValidacion",
    "cargar",
    "obtener",
    "recargar",
]
