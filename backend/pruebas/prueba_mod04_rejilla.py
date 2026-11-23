"""Pruebas de T-10: intensidad entre 0 y 1 sobre la rejilla fija de UT-03.

La prueba que pide el plan es que el vector normalizado quede dentro de 0 y 1
con el número de puntos acordado. Además se revisa el eje de 4000 a 400, que
cambiar UT-03 cambia la rejilla sin tocar código, y que el flujo completo
cumple CA-03.1 y CA-03.2 de punta a punta dentro de MOD-04.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from backend.preprocesamiento.procesador import procesar
from backend.preprocesamiento.rejilla import eje, normalizar, remuestrear
from backend.utilerias.configuracion import obtener as obtener_configuracion


def _procesar(carpeta: Path, nombre: str, configuracion=None):
    texto = (carpeta / nombre).read_text(encoding="ascii")
    resultado = procesar(nombre, texto, configuracion)
    assert resultado.valido, resultado.detalle
    return resultado.espectro


@pytest.mark.parametrize(
    "nombre",
    [
        "espectro-valido.jdx",
        "espectro-comprimido.jdx",
        "espectro-valido-900-puntos.csv",
        "espectro-porcentaje.csv",
    ],
)
def prueba_el_vector_queda_entre_0_y_1_con_los_puntos_de_ut03(
    carpeta_fixtures: Path, nombre: str
) -> None:
    procesamiento = obtener_configuracion().procesamiento
    espectro = _procesar(carpeta_fixtures, nombre)

    assert len(espectro.intensidad) == procesamiento.puntos_rejilla
    assert len(espectro.eje_cm1) == procesamiento.puntos_rejilla
    assert min(espectro.intensidad) == 0.0
    assert max(espectro.intensidad) == 1.0


def prueba_el_eje_va_del_mayor_al_menor_numero_de_onda(carpeta_fixtures: Path) -> None:
    menor, mayor = obtener_configuracion().procesamiento.rango_rejilla_cm1
    espectro = _procesar(carpeta_fixtures, "espectro-valido.jdx")

    assert espectro.eje_cm1[0] == mayor
    assert espectro.eje_cm1[-1] == menor
    assert all(a > b for a, b in zip(espectro.eje_cm1, espectro.eje_cm1[1:]))


def prueba_cambiar_la_rejilla_en_ut03_cambia_el_tamano(carpeta_fixtures: Path) -> None:
    configuracion = obtener_configuracion()
    otra = dataclasses.replace(
        configuracion,
        procesamiento=dataclasses.replace(configuracion.procesamiento, puntos_rejilla=50),
    )

    espectro = _procesar(carpeta_fixtures, "espectro-valido.jdx", otra)

    assert len(espectro.intensidad) == 50


def prueba_ca_03_1_el_csv_en_porcentaje_termina_igual_que_el_jdx_en_fraccion(
    carpeta_fixtures: Path,
) -> None:
    porcentaje = _procesar(carpeta_fixtures, "espectro-porcentaje.csv")
    fraccion = _procesar(carpeta_fixtures, "espectro-valido.jdx")

    assert porcentaje.unidad_original == "porcentaje"
    assert porcentaje.intensidad == pytest.approx(fraccion.intensidad, abs=1e-6)


def prueba_ca_03_2_descendente_y_ascendente_salen_identicos(
    carpeta_fixtures: Path,
) -> None:
    assert _procesar(carpeta_fixtures, "espectro-descendente.jdx") == _procesar(
        carpeta_fixtures, "espectro-valido.jdx"
    )


def prueba_lo_que_no_se_midio_queda_en_cero_y_se_avisa_el_tramo() -> None:
    puntos = [(1000.0 + i, float(i % 7)) for i in range(2001)]
    texto = "\n".join(f"{x},{y}" for x, y in puntos)
    resultado = procesar("e.csv", texto)

    espectro = resultado.espectro
    assert espectro.rango_medido_cm1 == (1000.0, 3000.0)
    for onda, valor in zip(espectro.eje_cm1, espectro.intensidad):
        if onda < 1000.0 or onda > 3000.0:
            assert valor == 0.0


def prueba_la_interpolacion_es_exacta_sobre_una_recta() -> None:
    puntos = [(x, 2.0 * x + 1.0) for x in (0.0, 10.0, 20.0)]

    valores, medido = remuestrear(puntos, eje(5, (0.0, 20.0)))

    assert medido == (0.0, 20.0)
    assert valores == pytest.approx([41.0, 31.0, 21.0, 11.0, 1.0])


def prueba_normalizar_deja_el_minimo_en_cero_y_el_maximo_en_uno() -> None:
    assert normalizar([2.0, None, 4.0, 3.0]) == [0.0, 0.0, 1.0, 0.5]


def prueba_procesar_no_escribe_en_disco(
    carpeta_fixtures: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RNF-09: el espectro se procesa solo en memoria."""
    import builtins

    abiertos: list[str] = []
    original = builtins.open

    def vigilado(archivo, modo="r", *args, **kwargs):
        if any(letra in modo for letra in "wax+"):
            abiertos.append(str(archivo))
        return original(archivo, modo, *args, **kwargs)

    texto = (carpeta_fixtures / "espectro-comprimido.jdx").read_text(encoding="ascii")
    monkeypatch.setattr(builtins, "open", vigilado)
    procesar("c.jdx", texto)

    assert abiertos == []
