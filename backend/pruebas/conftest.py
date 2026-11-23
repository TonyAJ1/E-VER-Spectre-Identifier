"""Apoyo compartido de las pruebas del backend.

Los archivos de prueba se reparten en dos grupos (sección 11 del plan):

- Los **chicos** están commiteados en `datos/pruebas/` y se usan tal cual.
- Los **pesados** —el de tamaño máximo exacto, el de un byte de más y el de
  ~3 MB— **no van al repositorio**: nadie quiere megabytes en el historial de
  git. Se generan aquí, una vez por corrida, en la carpeta temporal de pytest, y
  desaparecen con ella.

El tamaño máximo sale de UT-03, no de un número escrito aquí: si el equipo
cambia el límite, CA-01.2 y CA-02.2 siguen probando el límite de verdad.

La generación vive en `herramientas/`, fuera de la aplicación. Las pruebas la
importan de ahí para no tener una segunda copia de la misma lógica; ningún
módulo de `backend/` la importa.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.generador_espectros import csv_de_tamano_exacto
from herramientas.generar_fixtures import BYTES_TRES_MEGAS, DESDE, HASTA

RAIZ = Path(__file__).resolve().parents[2]

#: Los archivos de prueba commiteados.
CARPETA_FIXTURES = RAIZ / "datos" / "pruebas"


@pytest.fixture(scope="session")
def carpeta_fixtures() -> Path:
    """La carpeta de los archivos de prueba commiteados."""
    assert CARPETA_FIXTURES.is_dir(), (
        f"faltan los archivos de prueba en {CARPETA_FIXTURES}; "
        "regenérelos con «python -m herramientas.generar_fixtures»"
    )
    return CARPETA_FIXTURES


@pytest.fixture(scope="session")
def archivos_grandes(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    """Los tres archivos pesados, generados al arrancar la corrida.

    Devuelve las rutas por nombre corto: «maximo», «un_byte_de_mas» y
    «tres_megas».
    """
    configuracion = obtener_configuracion()
    maximo = configuracion.archivo.tamano_maximo_bytes
    minimos = configuracion.validacion.puntos_minimos

    carpeta = tmp_path_factory.mktemp("espectros_grandes")

    tamanos = {
        "maximo": maximo,
        "un_byte_de_mas": maximo + 1,
        "tres_megas": BYTES_TRES_MEGAS,
    }

    rutas: dict[str, Path] = {}
    for nombre, bytes_objetivo in tamanos.items():
        ruta = carpeta / f"espectro-{nombre}.csv"
        ruta.write_bytes(
            csv_de_tamano_exacto(
                bytes_objetivo, DESDE, HASTA, puntos_minimos=minimos
            )
        )
        rutas[nombre] = ruta
    return rutas


@pytest.fixture(scope="session")
def csv_tamano_maximo(archivos_grandes: dict[str, Path]) -> Path:
    """CSV válido de exactamente el tamaño máximo de UT-03 (CA-01.2)."""
    return archivos_grandes["maximo"]


@pytest.fixture(scope="session")
def csv_un_byte_de_mas(archivos_grandes: dict[str, Path]) -> Path:
    """CSV de un byte por encima del tamaño máximo (CA-02.2)."""
    return archivos_grandes["un_byte_de_mas"]


@pytest.fixture(scope="session")
def csv_tres_megas(archivos_grandes: dict[str, Path]) -> Path:
    """CSV válido de ~3 MB: pasa de 1 MB y obliga al temporal de FastAPI (RNF-09)."""
    return archivos_grandes["tres_megas"]


# --------------------------------------------------------------------------- #
# Navegador real para MOD-01 (T-06) y las pruebas de punta a punta (T-07)
# --------------------------------------------------------------------------- #

#: Variable de entorno opcional con la ruta de un Chromium ya instalado. Si no
#: está, Playwright usa el suyo («python -m playwright install chromium»).
VARIABLE_CHROMIUM = "EVER_CHROMIUM"

#: Variable de entorno opcional: carpeta donde guardar las capturas que sirven
#: de evidencia (sección 10 del plan). Fuera del repositorio.
VARIABLE_EVIDENCIA = "EVER_EVIDENCIA"

#: Carpeta del frontend (MOD-01 y servicios).
CARPETA_FRONTEND = RAIZ / "frontend"


@pytest.fixture(scope="module")
def navegador():
    """Un Chromium sin ventana por archivo de pruebas.

    Por archivo y no por corrida: mientras Playwright está abierto mantiene un
    bucle de eventos en el hilo principal, y las pruebas de MOD-02 necesitan
    `asyncio.run`. Al cerrar el navegador al final de cada archivo, el bucle
    se suelta antes de que lleguen las demás.
    """
    import os

    sync_api = pytest.importorskip(
        "playwright.sync_api",
        reason="falta Playwright: «pip install -r requirements.txt»",
    )
    ruta = os.environ.get(VARIABLE_CHROMIUM) or None
    with sync_api.sync_playwright() as playwright:
        try:
            chromium = playwright.chromium.launch(executable_path=ruta)
        except Exception as error:  # pragma: no cover - depende de la máquina
            pytest.fail(
                "no se pudo abrir Chromium. Instálelo una vez con "
                f"«python -m playwright install chromium» ({type(error).__name__})"
            )
        yield chromium
        chromium.close()


@pytest.fixture
def pagina(navegador):
    """Una pestaña limpia por prueba, del ancho de un celular (360 px)."""
    contexto = navegador.new_context(viewport={"width": 360, "height": 740})
    pestana = contexto.new_page()
    yield pestana
    contexto.close()


@pytest.fixture
def evidencia(request: pytest.FixtureRequest, tmp_path: Path):
    """Guarda una captura con el nombre de la prueba.

    Siempre se escribe en la carpeta temporal de la prueba; si existe la
    variable `EVER_EVIDENCIA`, también se copia ahí para la bitácora.
    """
    import os
    import shutil

    def guardar(pestana, nombre: str) -> Path:
        ruta = tmp_path / f"{nombre}.png"
        pestana.screenshot(path=str(ruta), full_page=True)
        destino = os.environ.get(VARIABLE_EVIDENCIA)
        if destino:
            Path(destino).mkdir(parents=True, exist_ok=True)
            shutil.copy(ruta, Path(destino) / ruta.name)
        return ruta

    return guardar
