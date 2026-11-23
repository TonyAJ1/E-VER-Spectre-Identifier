"""Pruebas de T-20: las plantillas de explicación de los 7 grupos.

La prueba del plan es de cobertura: los 7 grupos del catálogo tienen
plantilla. Además se revisa la mitigación del riesgo de contenido químico:
las regiones se toman del catálogo y no se reescriben a mano en la plantilla,
y cada plantilla dice qué fuentes se consultaron. La revisión cruzada y la del
profesor de química no se pueden probar con código: quedan en el campo
revisado_por, que hoy está vacío.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from backend.utilerias.catalogo import (
    IDS_ESPERADOS,
    RUTA_PLANTILLAS,
    ErrorDeCatalogo,
    cargar,
    cargar_plantillas,
)


def prueba_cobertura_los_7_grupos_tienen_plantilla() -> None:
    assert sorted(cargar_plantillas()) == list(IDS_ESPERADOS)


def prueba_las_plantillas_no_reescriben_los_numeros_de_las_regiones() -> None:
    catalogo = cargar()
    numeros_de_regiones = {
        f"{valor:g}"
        for grupo in catalogo.grupos
        for region in grupo.regiones_de_busqueda()
        for valor in region
    }
    hallazgos = []
    for identificador, plantilla in cargar_plantillas().items():
        for numero in re.findall(r"\d+", plantilla.por_que):
            if numero in numeros_de_regiones:
                hallazgos.append(f"{identificador}: {numero}")
    assert not hallazgos, f"números de región escritos a mano: {hallazgos}"


def prueba_cada_plantilla_dice_sus_fuentes() -> None:
    for plantilla in cargar_plantillas().values():
        assert len(plantilla.fuentes) >= 2


def prueba_la_de_n_h_explica_por_que_no_es_o_h() -> None:
    texto = cargar_plantillas()["GF-02"].por_que.lower()
    assert "o–h" in texto and "angost" in texto


def prueba_una_plantilla_de_un_grupo_que_no_existe_no_arranca(tmp_path: Path) -> None:
    datos = json.loads(RUTA_PLANTILLAS.read_text(encoding="utf-8"))
    datos["plantillas"][0]["grupo"] = "GF-99"
    ruta = tmp_path / "plantillas.json"
    ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ErrorDeCatalogo):
        cargar_plantillas(ruta)
