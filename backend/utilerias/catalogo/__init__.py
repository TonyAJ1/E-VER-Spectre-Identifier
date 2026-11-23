"""UT-01, catálogo de grupos funcionales.

Uso habitual:

    from backend.utilerias.catalogo import obtener as obtener_catalogo

    catalogo = obtener_catalogo()
    carbonilo = catalogo.grupo("GF-05")
"""

from backend.utilerias.catalogo.cargador import (
    IDS_ESPERADOS,
    RUTA_GRUPOS,
    Acompanante,
    Catalogo,
    ErrorDeCatalogo,
    Grupo,
    RegionAlterna,
    Regla,
    cargar,
    obtener,
)

__all__ = [
    "IDS_ESPERADOS",
    "RUTA_GRUPOS",
    "Acompanante",
    "Catalogo",
    "ErrorDeCatalogo",
    "Grupo",
    "RegionAlterna",
    "Regla",
    "cargar",
    "obtener",
]
