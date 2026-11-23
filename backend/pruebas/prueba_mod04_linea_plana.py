"""Pruebas de T-11: el espectro sin señal analizable.

CA-03.3 pide que, con una intensidad constante, el sistema no falle e informe
que el espectro no contiene señal analizable. Una línea plana pasa la
validación de MOD-03 porque tiene puntos y rango de sobra; es MOD-04 quien se
da cuenta al intentar normalizarla.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.preprocesamiento.procesador import procesar
from backend.preprocesamiento.rejilla import es_plano, normalizar
from backend.utilerias import mensajes
from backend.validacion import validar


def prueba_ca_03_3_la_linea_plana_no_falla_e_informa_sin_senal(
    carpeta_fixtures: Path,
) -> None:
    texto = (carpeta_fixtures / "espectro-linea-plana.csv").read_text(encoding="ascii")
    assert validar("plano.csv", texto).valido, "la línea plana debe pasar MOD-03"

    resultado = procesar("plano.csv", texto)

    assert resultado.valido is False
    assert resultado.codigo == mensajes.SIN_SENAL
    assert resultado.espectro is None
    assert "no contiene señal analizable" in mensajes.obtener(mensajes.SIN_SENAL).texto


@pytest.mark.parametrize("valor", [0.0, 0.5, 1.0, 87.3])
def prueba_cualquier_valor_constante_es_linea_plana(valor: float) -> None:
    texto = "\n".join(f"{400 + i * 4},{valor}" for i in range(901))

    resultado = procesar("plano.csv", texto)

    assert resultado.codigo == mensajes.SIN_SENAL


def prueba_una_variacion_pequena_pero_real_no_es_linea_plana() -> None:
    assert not es_plano([0.5, 0.5, 0.5001])


def prueba_normalizar_una_linea_plana_no_divide_entre_cero() -> None:
    assert normalizar([0.3, None, 0.3]) == [0.0, 0.0, 0.0]
