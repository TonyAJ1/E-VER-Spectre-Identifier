"""Fusión de la evidencia y umbral de MOD-06 (tarea T-17).

Para cada grupo la confianza es el peso de las reglas por su puntaje más el
peso del modelo por su probabilidad. Se reporta el grupo si su confianza llega
al umbral, y la región siempre sale de la vía de reglas y del catálogo. El
umbral y los pesos llegan desde UT-03 por medio de quien llama al motor.

La salida es el contrato de la sección 5 del diseño de MOD-06.
"""

from __future__ import annotations

from typing import Any

#: Decimales con que se compara la confianza contra el umbral. Evita que un
#: 0.6 calculado como 0.5999999999 quede fuera por un error de redondeo de la
#: computadora (CA-05.3).
DECIMALES = 4


def confianza(puntaje_regla: float, prob_ml: float | None, peso_reglas: float, peso_ml: float) -> float:
    ml = prob_ml if prob_ml is not None else 0.0
    return round(peso_reglas * puntaje_regla + peso_ml * ml, DECIMALES)


def alcanza(valor: float, umbral: float) -> bool:
    return round(valor, DECIMALES) >= round(umbral, DECIMALES)


def fusionar(
    evaluaciones,
    probabilidades_ml: dict[str, float] | None,
    grupos,
    *,
    umbral: float,
    peso_reglas: float,
    peso_ml: float,
) -> dict[str, Any]:
    por_id = {grupo.id: grupo for grupo in grupos}
    detecciones = []
    for evaluacion in evaluaciones:
        ml = None if probabilidades_ml is None else probabilidades_ml.get(evaluacion.grupo)
        valor = confianza(evaluacion.puntaje, ml, peso_reglas, peso_ml)
        if not alcanza(valor, umbral):
            continue
        grupo = por_id[evaluacion.grupo]
        detecciones.append(
            {
                "grupo": evaluacion.grupo,
                "confianza": valor,
                "region_cm1": list(_region(grupo, evaluacion.pico_cm1)),
                "pico_cm1": evaluacion.pico_cm1,
                "evidencia": {"regla": evaluacion.puntaje, "ml": ml},
            }
        )
    detecciones.sort(key=lambda d: (-d["confianza"], d["grupo"]))
    return {
        "detecciones": detecciones,
        "sin_detecciones": not detecciones,
        "umbral": umbral,
    }


def _region(grupo, pico: float | None) -> tuple[float, float]:
    """La región donde cayó el pico. Si el pico cae en una región alterna,
    como la de los ácidos para O–H, se usa esa; si no, la principal."""
    if pico is not None:
        for region in grupo.regiones_de_busqueda():
            if region[0] <= pico <= region[1]:
                return region
    return grupo.region_cm1
