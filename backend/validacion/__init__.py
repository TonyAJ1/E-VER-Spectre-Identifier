"""MOD-03 · Validador.

Responde dos preguntas distintas, en dos tareas distintas:

- **T-04:** «¿el contenido es de verdad del formato que declara?»
  (`revisar_formato`)
- **T-05:** «¿cumple los requisitos de puntos y rango?» (`validar` corre las
  dos, en ese orden; es lo que usa la API)

Uso habitual (la orquestación vive en `backend/api/`, T-07):

    from backend.validacion import validar

    veredicto = validar(recepcion.nombre, recepcion.contenido)
    if not veredicto.valido:
        ...  # veredicto.codigo se traduce con UT-02
"""

from backend.validacion.validador import (
    CAPA_COHERENCIA,
    CAPA_ESTRUCTURA,
    CAPA_EXTENSION,
    CAPA_PUNTOS,
    CAPA_RANGO,
    CAPA_TAMANO,
    CAPA_TEXTO,
    COLUMNAS_CSV,
    EXTENSION_CSV,
    EXTENSION_JDX,
    FILAS_A_REVISAR,
    FILAS_MINIMAS,
    SEPARADOR_CSV,
    SEPARADOR_CSV_PUNTO_Y_COMA,
    SEPARADORES_CSV,
    Veredicto,
    extension_de,
    revisar_formato,
    validar,
)

__all__ = [
    "CAPA_COHERENCIA",
    "CAPA_ESTRUCTURA",
    "CAPA_EXTENSION",
    "CAPA_PUNTOS",
    "CAPA_RANGO",
    "CAPA_TAMANO",
    "CAPA_TEXTO",
    "COLUMNAS_CSV",
    "EXTENSION_CSV",
    "EXTENSION_JDX",
    "FILAS_A_REVISAR",
    "FILAS_MINIMAS",
    "SEPARADOR_CSV",
    "SEPARADOR_CSV_PUNTO_Y_COMA",
    "SEPARADORES_CSV",
    "Veredicto",
    "extension_de",
    "revisar_formato",
    "validar",
]
