"""Pruebas de T-08: MOD-04 lee .jdx y .csv al mismo conjunto de pares.

El plan pide dos pruebas para cerrar la tarea. La primera usa un archivo real
de NIST con datos comprimidos y revisa que se lean todos los puntos que dice
##NPOINTS=. La segunda usa un .jdx con YFACTOR distinto de 1 y su CSV
equivalente, que tienen que dar los mismos valores.

El archivo real no se puede guardar en el repositorio por su licencia. Cuando
no está en datos/referencia/ esa prueba se salta y lo dice. Para no quedarse
sin probar la descompresión, hay además un archivo fabricado que guarda los
mismos puntos de espectro-valido.jdx en la misma forma comprimida que usa NIST.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from backend.preprocesamiento.lector import (
    ABSORBANCIA,
    DESCONOCIDA,
    TRANSMITANCIA,
    ArchivoIlegible,
    descomprimir,
    leer,
)
from backend.utilerias import mensajes

RAIZ = Path(__file__).resolve().parents[2]
MANIFIESTO = RAIZ / "herramientas" / "espectros_nist.json"

#: Los números de onda del .jdx fabricado se escriben con cuatro decimales y
#: los del comprimido se calculan con FIRSTX, LASTX y NPOINTS. La diferencia
#: es de redondeo y queda muy por debajo de esta tolerancia.
TOLERANCIA_ONDA = 1e-3
TOLERANCIA_INTENSIDAD = 1e-9


def _texto(carpeta: Path, nombre: str) -> str:
    return (carpeta / nombre).read_text(encoding="ascii")


def _iguales(a, b, tolerancia_onda=TOLERANCIA_ONDA) -> None:
    assert len(a) == len(b)
    for (x1, y1), (x2, y2) in zip(a, b):
        assert abs(x1 - x2) <= tolerancia_onda
        assert abs(y1 - y2) <= TOLERANCIA_INTENSIDAD


# Mismo espectro, distinto formato


def prueba_un_jdx_y_un_csv_del_mismo_espectro_dan_los_mismos_pares(
    carpeta_fixtures: Path,
) -> None:
    jdx = leer("espectro.jdx", _texto(carpeta_fixtures, "espectro-valido.jdx"))
    csv = leer("espectro.csv", _texto(carpeta_fixtures, "espectro-valido-900-puntos.csv"))

    assert len(jdx.pares) == 900
    _iguales(jdx.pares, csv.pares, tolerancia_onda=0)


def prueba_limite_el_jdx_con_yfactor_da_lo_mismo_que_su_csv(
    carpeta_fixtures: Path,
) -> None:
    """Prueba del plan para RF-03 en T-08: la escala se aplicó."""
    con_factor = leer("factores.jdx", _texto(carpeta_fixtures, "espectro-factores.jdx"))
    csv = leer("espectro.csv", _texto(carpeta_fixtures, "espectro-valido-900-puntos.csv"))

    _iguales(con_factor.pares, csv.pares, tolerancia_onda=0)


def prueba_el_jdx_comprimido_da_los_mismos_puntos_que_el_normal(
    carpeta_fixtures: Path,
) -> None:
    comprimido = leer("c.jdx", _texto(carpeta_fixtures, "espectro-comprimido.jdx"))
    normal = leer("n.jdx", _texto(carpeta_fixtures, "espectro-valido.jdx"))

    assert comprimido.unidad == TRANSMITANCIA
    _iguales(comprimido.pares, normal.pares)


# Archivo real de NIST


def _espectros_reales() -> list[dict]:
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    carpeta = RAIZ / manifiesto["carpeta_destino"]
    return [dict(e, ruta=carpeta / e["archivo"]) for e in manifiesto["espectros"]]


@pytest.mark.parametrize(
    "espectro", _espectros_reales(), ids=lambda e: e["compuesto"]
)
def prueba_normal_el_archivo_real_de_nist_se_lee_completo(espectro: dict) -> None:
    ruta: Path = espectro["ruta"]
    if not ruta.is_file():
        pytest.skip(
            f"falta {ruta.name} en datos/referencia; bájelo con "
            "python -m herramientas.descargar_espectros_nist"
        )

    lectura = leer(ruta.name, ruta.read_text(encoding="latin-1"))

    assert len(lectura.pares) == espectro["puntos"]
    ondas = [onda for onda, _ in lectura.pares]
    assert min(ondas) == pytest.approx(min(espectro["primer_x"], espectro["ultimo_x"]), abs=0.01)
    assert max(ondas) == pytest.approx(max(espectro["primer_x"], espectro["ultimo_x"]), abs=0.01)


# Lo que no cuadra se rechaza, nunca se lee mal en silencio


def prueba_si_los_puntos_no_coinciden_con_npoints_se_rechaza(
    carpeta_fixtures: Path,
) -> None:
    texto = _texto(carpeta_fixtures, "espectro-comprimido.jdx").replace(
        "##NPOINTS=900", "##NPOINTS=901"
    )
    with pytest.raises(ArchivoIlegible):
        leer("c.jdx", texto)


def prueba_si_el_valor_de_comprobacion_no_coincide_se_rechaza() -> None:
    # La segunda línea debería empezar repitiendo el 3 con que acaba la primera.
    with pytest.raises(ArchivoIlegible):
        descomprimir(["100A J J", "200E J"])


def prueba_un_caracter_desconocido_en_los_datos_se_rechaza() -> None:
    with pytest.raises(ArchivoIlegible):
        descomprimir(["100A J ~ J"])


def prueba_unas_unidades_que_no_son_de_infrarrojo_se_rechazan(
    carpeta_fixtures: Path,
) -> None:
    texto = _texto(carpeta_fixtures, "espectro-valido.jdx").replace(
        "##YUNITS=TRANSMITTANCE", "##YUNITS=ARBITRARY UNITS"
    )
    with pytest.raises(ArchivoIlegible):
        leer("e.jdx", texto)


def prueba_el_mensaje_de_datos_ilegibles_trae_motivo_y_accion() -> None:
    mensaje = mensajes.obtener(mensajes.DATOS_ILEGIBLES)
    assert mensaje.texto.strip() and mensaje.accion.strip()


# Las cuatro formas de guardar números de JCAMP-DX


@pytest.mark.parametrize(
    ("lineas", "esperado"),
    [
        (["100 1 2 3"], [1, 2, 3]),  # AFFN, números comunes
        (["100+1+2-3"], [1, 2, -3]),  # PAC, el signo separa
        (["100A B c"], [1, 2, -3]),  # SQZ, la letra lleva la primera cifra
        (["100A J J"], [1, 2, 3]),  # DIF, diferencias con el anterior
        (["100A JT"], [1, 2, 3]),  # DUP, la T repite dos veces la diferencia
        (["100A1 %U"], [11, 11, 11, 11]),  # DIF cero repetido tres veces
        (["100A J J", "200C J"], [1, 2, 3, 4]),  # la segunda línea repite el 3
        (["100 1.5E+01 2"], [15, 2]),  # exponente de un número común
    ],
)
def prueba_descomprimir_las_formas_de_la_norma(lineas, esperado) -> None:
    assert descomprimir(lineas) == pytest.approx(esperado)


# CSV


def prueba_csv_con_punto_y_coma_coma_decimal_y_encabezado() -> None:
    texto = "numero de onda;absorbancia\n400,5;0,25\n401,5;0,30\n"

    lectura = leer("e.csv", texto)

    assert lectura.pares == ((400.5, 0.25), (401.5, 0.30))
    assert lectura.unidad == ABSORBANCIA


def prueba_csv_sin_encabezado_no_sabe_su_unidad(carpeta_fixtures: Path) -> None:
    lectura = leer("e.csv", _texto(carpeta_fixtures, "espectro-valido-900-puntos.csv"))
    assert lectura.unidad == DESCONOCIDA


def prueba_csv_con_una_fila_rota_a_la_mitad_se_rechaza() -> None:
    with pytest.raises(ArchivoIlegible):
        leer("e.csv", "400,0.5\n401,abc\n402,0.6\n")
