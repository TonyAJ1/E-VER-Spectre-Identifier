"""Pruebas de T-16 en plan B: la vía de aprendizaje automático.

No hay modelo entrenado, porque no hay conjunto de espectros etiquetados. Lo
que sí se puede probar es que la vía lo dice con claridad en lugar de inventar
probabilidades, y que UT-03 tiene el peso del modelo en cero, que es el plan B
del diseño de MOD-06.
"""

from __future__ import annotations

import pytest

from backend.utilerias.configuracion import cargar
from motor_identificacion.modelo.via_ml import ModeloNoDisponible, ViaML


def prueba_sin_pesos_la_via_dice_que_no_esta_disponible(tmp_path) -> None:
    via = ViaML(tmp_path)

    assert via.disponible is False
    with pytest.raises(ModeloNoDisponible):
        via.predecir([4000.0, 400.0], [0.0, 1.0])


def prueba_ut03_aplica_el_plan_b_con_el_peso_del_modelo_en_cero() -> None:
    import json

    datos = json.loads(cargar().ruta.read_text(encoding="utf-8"))
    assert datos["motor"]["peso_ml"] == 0
    assert datos["motor"]["peso_reglas"] == 1
