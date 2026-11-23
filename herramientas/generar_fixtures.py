"""Escribe los archivos de prueba fabricados en `datos/pruebas/`.

Uso, desde la raíz del repositorio:

    python -m herramientas.generar_fixtures

Vuelve a escribir los mismos bytes en cada corrida: los archivos son
deterministas, así que si no cambia el generador, git no ve cambios.

Los archivos **pesados** (el de tamaño máximo exacto, el de un byte de más y el
de ~3 MB) **no** se escriben aquí: las pruebas los generan al arrancar, para no
meter megabytes al historial de git (sección 11 del plan). Si los necesita a
mano para una evidencia:

    python -m herramientas.generar_fixtures --grandes <carpeta>

**Esto no es código de la aplicación**: vive en `herramientas/` y ningún módulo
de `backend/` lo importa.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:  # permite correrlo como script o con -m
    sys.path.insert(0, str(RAIZ))

from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.generador_espectros import (
    binario_disfrazado,
    csv_de_tamano_exacto,
    csv_sintetico,
    jdx_comprimido,
    jdx_con_factores,
    jdx_sintetico,
    png_minimo,
)

CARPETA_PRUEBAS = RAIZ / "datos" / "pruebas"

#: Rango que cubren los archivos válidos. Más amplio que el exigido por UT-03,
#: como el eje de la gráfica del incremento 2.
DESDE, HASTA = 400.0, 4000.0

#: El CSV «normal» de CA-02.1: dos columnas, 900 puntos, 400–4000.
PUNTOS_CSV_NORMAL = 900

#: Tamaño aproximado del CSV de las pruebas RNF-09: pasa de 1 MB, que es lo que
#: obliga a FastAPI a crear el archivo temporal en disco.
BYTES_TRES_MEGAS = 3 * 1024 * 1024


def generar(carpeta: Path = CARPETA_PRUEBAS) -> list[tuple[str, int]]:
    """Escribe los archivos commiteables y devuelve (nombre, bytes) de cada uno."""
    configuracion = obtener_configuracion()
    minimos = configuracion.validacion.puntos_minimos
    rango_minimo, rango_maximo = configuracion.validacion.rango_requerido_cm1

    carpeta.mkdir(parents=True, exist_ok=True)

    archivos: dict[str, bytes] = {
        # --- Casos válidos ------------------------------------------------- #
        "espectro-valido.jdx": jdx_sintetico(
            "ESPECTRO SINTETICO DE PRUEBA",
            PUNTOS_CSV_NORMAL,
            DESDE,
            HASTA,
            nota=(
                "CA-01.1 - archivo fabricado para pruebas, sin datos de "
                "terceros. Estructura valida: etiquetas obligatorias, puntos "
                "y rango suficientes."
            ),
        ),
        "espectro-valido-900-puntos.csv": csv_sintetico(
            PUNTOS_CSV_NORMAL, DESDE, HASTA
        ),
        "espectro-puntos-minimos.csv": csv_sintetico(minimos, DESDE, HASTA),
        # --- Casos de rechazo ---------------------------------------------- #
        "espectro-un-punto-menos.csv": csv_sintetico(minimos - 1, DESDE, HASTA),
        "espectro-rango-corto.csv": csv_sintetico(
            PUNTOS_CSV_NORMAL, rango_minimo + 100, rango_maximo
        ),
        "espectro-truncado.jdx": jdx_sintetico(
            "ESPECTRO TRUNCADO DE PRUEBA",
            PUNTOS_CSV_NORMAL,
            DESDE,
            HASTA,
            nota="CA-02.4 - a este archivo le falta la etiqueta de cierre.",
            con_end=False,
        ),
        # --- Incremento 2: lectura de MOD-04 ------------------------------ #
        "espectro-comprimido.jdx": jdx_comprimido(
            "ESPECTRO SINTETICO COMPRIMIDO",
            PUNTOS_CSV_NORMAL,
            DESDE,
            HASTA,
            nota=(
                "T-08 - los mismos puntos de espectro-valido.jdx guardados en "
                "forma DIFDUP con XFACTOR y YFACTOR, como los archivos de "
                "las bases publicas."
            ),
        ),
        "espectro-factores.jdx": jdx_con_factores(
            "ESPECTRO SINTETICO CON FACTORES",
            PUNTOS_CSV_NORMAL,
            DESDE,
            HASTA,
            nota=(
                "T-08 - los mismos puntos de espectro-valido.jdx con las "
                "intensidades multiplicadas por mil y YFACTOR=0.001."
            ),
        ),
        "archivo-vacio.csv": b"",
        "binario-disfrazado.csv": binario_disfrazado(),
        "imagen.png": png_minimo(),
    }

    escritos: list[tuple[str, int]] = []
    for nombre, contenido in archivos.items():
        # Binario a propósito: los bytes deben quedar tal cual, sin que Windows
        # convierta los saltos de línea.
        (carpeta / nombre).write_bytes(contenido)
        escritos.append((nombre, len(contenido)))
    return escritos


def generar_grandes(carpeta: Path) -> list[tuple[str, int]]:
    """Escribe los tres archivos pesados, que no van al repositorio."""
    configuracion = obtener_configuracion()
    maximo = configuracion.archivo.tamano_maximo_bytes
    minimos = configuracion.validacion.puntos_minimos

    carpeta.mkdir(parents=True, exist_ok=True)
    archivos = {
        "espectro-tamano-maximo.csv": csv_de_tamano_exacto(
            maximo, DESDE, HASTA, puntos_minimos=minimos
        ),
        "espectro-un-byte-de-mas.csv": csv_de_tamano_exacto(
            maximo + 1, DESDE, HASTA, puntos_minimos=minimos
        ),
        "espectro-tres-megas.csv": csv_de_tamano_exacto(
            BYTES_TRES_MEGAS, DESDE, HASTA, puntos_minimos=minimos
        ),
    }

    escritos: list[tuple[str, int]] = []
    for nombre, contenido in archivos.items():
        (carpeta / nombre).write_bytes(contenido)
        escritos.append((nombre, len(contenido)))
    return escritos


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument(
        "--grandes",
        metavar="CARPETA",
        type=Path,
        help=(
            "escribe además los archivos pesados en esa carpeta (no en el "
            "repositorio)"
        ),
    )
    argumentos = analizador.parse_args()

    print(f"Archivos de prueba en {CARPETA_PRUEBAS}:")
    for nombre, bytes_ in generar():
        print(f"  {nombre:<34} {bytes_:>10,} bytes")

    if argumentos.grandes:
        print(f"\nArchivos pesados en {argumentos.grandes} (fuera del repositorio):")
        for nombre, bytes_ in generar_grandes(argumentos.grandes):
            print(f"  {nombre:<34} {bytes_:>10,} bytes")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
