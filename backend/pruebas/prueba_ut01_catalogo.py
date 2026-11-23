"""Pruebas de T-14: el catálogo de los 7 grupos funcionales en UT-01.

La prueba del plan es de cobertura: los 7 grupos tienen región, rango e
intensidad o forma. Además se revisa que las regiones coincidan con la tabla
de Requerimientos V3 (sección 6.2), que el catálogo sea de solo lectura y que
un catálogo incompleto impida arrancar.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from backend.utilerias.catalogo import (
    IDS_ESPERADOS,
    RUTA_GRUPOS,
    ErrorDeCatalogo,
    cargar,
)

#: Las regiones de la tabla 6.2 de Requerimientos V3, copiadas aquí a mano a
#: propósito: si alguien cambia el JSON, esta prueba lo nota.
REGIONES_DE_REQUERIMIENTOS = {
    "GF-01": (3200.0, 3550.0),
    "GF-02": (3300.0, 3500.0),
    "GF-03": (2850.0, 2960.0),
    "GF-04": (2210.0, 2260.0),
    "GF-05": (1670.0, 1780.0),
    "GF-06": (1620.0, 1680.0),
    "GF-07": (1450.0, 1600.0),
}


def prueba_cobertura_los_7_grupos_tienen_region_rango_e_intensidad() -> None:
    catalogo = cargar()

    assert tuple(grupo.id for grupo in catalogo.grupos) == IDS_ESPERADOS
    for grupo in catalogo.grupos:
        assert grupo.nombre and grupo.enlace and grupo.rasgo
        assert grupo.intensidad and grupo.forma
        menor, mayor = grupo.region_cm1
        assert 0 < menor < mayor


def prueba_las_regiones_son_las_de_requerimientos() -> None:
    catalogo = cargar()
    for identificador, region in REGIONES_DE_REQUERIMIENTOS.items():
        assert catalogo.grupo(identificador).region_cm1 == region


def prueba_el_o_h_de_los_acidos_tiene_su_region_alterna() -> None:
    grupo = cargar().grupo("GF-01")
    assert (2500.0, 3300.0) in grupo.regiones_de_busqueda()


def prueba_alqueno_y_aromatico_piden_su_c_h_por_encima_de_3000() -> None:
    catalogo = cargar()
    for identificador in ("GF-06", "GF-07"):
        acompanante = catalogo.grupo(identificador).regla.acompanante
        assert acompanante is not None
        assert acompanante.region_cm1[0] >= 3000


def prueba_el_catalogo_es_de_solo_lectura() -> None:
    grupo = cargar().grupo("GF-05")
    with pytest.raises(dataclasses.FrozenInstanceError):
        grupo.region_cm1 = (1, 2)  # type: ignore[misc]


def _escribir(tmp_path: Path, datos: dict) -> Path:
    ruta = tmp_path / "grupos.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    return ruta


def prueba_si_falta_un_grupo_no_arranca(tmp_path: Path) -> None:
    datos = json.loads(RUTA_GRUPOS.read_text(encoding="utf-8"))
    datos["grupos"].pop()
    with pytest.raises(ErrorDeCatalogo):
        cargar(_escribir(tmp_path, datos))


def prueba_si_a_un_grupo_le_falta_su_region_no_arranca(tmp_path: Path) -> None:
    datos = json.loads(RUTA_GRUPOS.read_text(encoding="utf-8"))
    del datos["grupos"][4]["region_cm1"]
    with pytest.raises(ErrorDeCatalogo):
        cargar(_escribir(tmp_path, datos))


def prueba_si_no_existe_el_archivo_no_arranca(tmp_path: Path) -> None:
    with pytest.raises(ErrorDeCatalogo):
        cargar(tmp_path / "no-existe.json")
