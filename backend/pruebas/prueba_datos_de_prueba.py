"""Pruebas de T-0R · los archivos de prueba son lo que dicen ser.

Estas pruebas no ejercitan la aplicación: **verifican los datos de prueba**
antes de que T-03 y T-04 los usen. Si un archivo de prueba miente, las pruebas
que dependen de él pasan sin demostrar nada, que es justo el riesgo del Paso 8.

Por eso aquí se cuentan filas y se miran mínimos y máximos a mano, en lugar de
usar un lector del sistema: todavía no existe (es MOD-03/MOD-04) y, si
existiera, probar un archivo con el mismo código que se va a probar con él no
diría gran cosa.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from backend.utilerias.configuracion import obtener as obtener_configuracion
from herramientas.generar_fixtures import PUNTOS_CSV_NORMAL, generar

# --------------------------------------------------------------------------- #
# Apoyo
# --------------------------------------------------------------------------- #


def _pares(ruta: Path) -> list[tuple[float, float]]:
    """Los pares (número de onda, intensidad) de un CSV de dos columnas."""
    pares: list[tuple[float, float]] = []
    for linea in ruta.read_text(encoding="ascii").splitlines():
        if not linea.strip():
            continue
        onda, intensidad = linea.split(",")
        pares.append((float(onda), float(intensidad)))
    return pares


def _cubre_el_rango_requerido(pares: list[tuple[float, float]]) -> bool:
    minimo, maximo = obtener_configuracion().validacion.rango_requerido_cm1
    ondas = [onda for onda, _ in pares]
    return min(ondas) <= minimo and max(ondas) >= maximo


# --------------------------------------------------------------------------- #
# Están todos
# --------------------------------------------------------------------------- #

ESPERADOS = (
    "espectro-valido.jdx",
    "espectro-valido-900-puntos.csv",
    "espectro-puntos-minimos.csv",
    "espectro-un-punto-menos.csv",
    "espectro-rango-corto.csv",
    "espectro-truncado.jdx",
    "espectro-comprimido.jdx",
    "espectro-factores.jdx",
    "espectro-descendente.jdx",
    "espectro-porcentaje.csv",
    "espectro-linea-plana.csv",
    "archivo-vacio.csv",
    "binario-disfrazado.csv",
    "imagen.png",
)


@pytest.mark.parametrize("nombre", ESPERADOS)
def prueba_el_archivo_de_prueba_existe(carpeta_fixtures: Path, nombre: str) -> None:
    assert (carpeta_fixtures / nombre).exists()


def prueba_la_carpeta_trae_su_nota_de_origen(carpeta_fixtures: Path) -> None:
    """Cada archivo necesita decir qué CA cubre y de dónde salió (T-0R)."""
    leeme = carpeta_fixtures / "LEEME.md"
    assert leeme.is_file(), "falta datos/pruebas/LEEME.md"

    texto = leeme.read_text(encoding="utf-8")
    faltantes = [nombre for nombre in ESPERADOS if nombre not in texto]
    assert not faltantes, f"LEEME.md no menciona: {faltantes}"


def prueba_no_hay_datos_de_nist_en_los_archivos_commiteados(
    carpeta_fixtures: Path,
) -> None:
    """Los archivos de prueba son fabricados: ni una línea de NIST ni de
    Coblentz, que es lo que permite commitearlos (sección «Licencias»)."""
    rastros = ("coblentz", "nist", "u.s. secretary of commerce", "cas registry")
    hallazgos: list[str] = []

    for ruta in sorted(carpeta_fixtures.iterdir()):
        if ruta.name == "LEEME.md" or not ruta.is_file():
            continue
        texto = ruta.read_bytes().decode("latin-1").lower()
        hallazgos += [f"{ruta.name}: {rastro}" for rastro in rastros if rastro in texto]

    assert not hallazgos, f"estos archivos traen rastros de datos reales: {hallazgos}"


# --------------------------------------------------------------------------- #
# Casos válidos
# --------------------------------------------------------------------------- #


def prueba_el_jdx_valido_tiene_la_estructura_que_pide_mod_03(
    carpeta_fixtures: Path,
) -> None:
    """CA-01.1: etiquetas obligatorias de UT-03, `##TITLE=` en la primera línea,
    `##END=` en la última y una etiqueta de datos."""
    configuracion = obtener_configuracion()
    lineas = (
        (carpeta_fixtures / "espectro-valido.jdx")
        .read_text(encoding="ascii")
        .splitlines()
    )

    assert lineas[0].startswith("##TITLE=")
    assert lineas[-1].startswith("##END=")

    texto = "\n".join(lineas)
    for etiqueta in configuracion.validacion.jcamp_etiquetas_obligatorias:
        assert etiqueta in texto, f"falta la etiqueta {etiqueta}"
    assert any(
        etiqueta in texto
        for etiqueta in configuracion.validacion.jcamp_etiquetas_datos_una_de
    )


def prueba_el_csv_normal_es_el_de_ca_02_1(carpeta_fixtures: Path) -> None:
    """CA-02.1: dos columnas, 900 puntos, rango 400–4000."""
    pares = _pares(carpeta_fixtures / "espectro-valido-900-puntos.csv")

    assert len(pares) == PUNTOS_CSV_NORMAL
    assert min(onda for onda, _ in pares) == pytest.approx(400)
    assert max(onda for onda, _ in pares) == pytest.approx(4000)
    assert _cubre_el_rango_requerido(pares)
    assert all(onda > 0 for onda, _ in pares), "los números de onda son positivos"


def prueba_el_csv_del_minimo_exacto_tiene_los_puntos_de_ut03(
    carpeta_fixtures: Path,
) -> None:
    """CA-02.6, mitad válida: exactamente los puntos mínimos, y cubriendo el
    rango, para que el conteo sea la única razón posible de rechazo."""
    pares = _pares(carpeta_fixtures / "espectro-puntos-minimos.csv")

    assert len(pares) == obtener_configuracion().validacion.puntos_minimos
    assert _cubre_el_rango_requerido(pares)


# --------------------------------------------------------------------------- #
# Casos de rechazo
# --------------------------------------------------------------------------- #


def prueba_el_csv_de_un_punto_menos_solo_falla_por_el_conteo(
    carpeta_fixtures: Path,
) -> None:
    """CA-02.6, mitad de rechazo: un punto por debajo del mínimo de UT-03."""
    pares = _pares(carpeta_fixtures / "espectro-un-punto-menos.csv")

    assert len(pares) == obtener_configuracion().validacion.puntos_minimos - 1
    assert _cubre_el_rango_requerido(pares), (
        "debe cubrir el rango: si no, el rechazo podría venir de ahí y CA-02.6 "
        "no probaría el conteo"
    )


def prueba_el_csv_de_rango_corto_solo_falla_por_el_rango(
    carpeta_fixtures: Path,
) -> None:
    """CA-02.3: no alcanza el extremo inferior del rango requerido, pero trae
    puntos de sobra, así que el rango es la única razón de rechazo."""
    configuracion = obtener_configuracion()
    rango_minimo, rango_maximo = configuracion.validacion.rango_requerido_cm1
    pares = _pares(carpeta_fixtures / "espectro-rango-corto.csv")

    assert len(pares) >= configuracion.validacion.puntos_minimos
    assert min(onda for onda, _ in pares) > rango_minimo
    assert max(onda for onda, _ in pares) == pytest.approx(rango_maximo)
    assert not _cubre_el_rango_requerido(pares)


def prueba_el_archivo_vacio_pesa_cero(carpeta_fixtures: Path) -> None:
    """CA-02.4, primera mitad."""
    assert (carpeta_fixtures / "archivo-vacio.csv").stat().st_size == 0


def prueba_el_jdx_truncado_no_tiene_la_etiqueta_de_cierre(
    carpeta_fixtures: Path,
) -> None:
    """CA-02.4, segunda mitad: `.jdx` cortado, sin `##END=`."""
    texto = (carpeta_fixtures / "espectro-truncado.jdx").read_text(encoding="ascii")

    assert texto.startswith("##TITLE=")
    assert "##END=" not in texto
    assert "##XYDATA=" in texto, "lo que falta es el cierre, no los datos"


def prueba_el_binario_disfrazado_trae_bytes_que_no_son_texto(
    carpeta_fixtures: Path,
) -> None:
    """CA-02.5: la extensión es admitida, el contenido no. El rechazo tiene que
    venir del contenido."""
    ruta = carpeta_fixtures / "binario-disfrazado.csv"
    datos = ruta.read_bytes()

    assert ruta.suffix in obtener_configuracion().archivo.formatos_permitidos
    assert b"\x00" in datos, "sin bytes nulos no prueba nada"


def prueba_la_imagen_no_es_un_formato_admitido(carpeta_fixtures: Path) -> None:
    """CA-01.3: un formato que la aplicación no acepta."""
    ruta = carpeta_fixtures / "imagen.png"

    assert ruta.suffix not in obtener_configuracion().archivo.formatos_permitidos
    assert ruta.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "es un PNG de verdad"


# --------------------------------------------------------------------------- #
# Los archivos pesados, generados al arrancar la corrida
# --------------------------------------------------------------------------- #


def prueba_el_csv_de_tamano_maximo_pesa_el_limite_exacto(
    csv_tamano_maximo: Path,
) -> None:
    """CA-01.2: exactamente el tamaño máximo de UT-03, al byte."""
    configuracion = obtener_configuracion()
    pares = _pares(csv_tamano_maximo)

    assert csv_tamano_maximo.stat().st_size == configuracion.archivo.tamano_maximo_bytes
    assert len(pares) >= configuracion.validacion.puntos_minimos
    assert _cubre_el_rango_requerido(pares), "debe ser válido en todo lo demás"


def prueba_el_csv_de_un_byte_de_mas_pasa_el_limite_por_uno(
    csv_un_byte_de_mas: Path,
) -> None:
    """CA-02.2: el anterior más un byte."""
    maximo = obtener_configuracion().archivo.tamano_maximo_bytes

    assert csv_un_byte_de_mas.stat().st_size == maximo + 1


def prueba_el_csv_de_tres_megas_obliga_al_temporal_en_disco(
    csv_tres_megas: Path,
) -> None:
    """RNF-09: pasa de 1 MB, que es cuando FastAPI escribe un temporal."""
    configuracion = obtener_configuracion()
    tamano = csv_tres_megas.stat().st_size

    assert tamano > 1024 * 1024
    assert tamano < configuracion.archivo.tamano_maximo_bytes
    assert _cubre_el_rango_requerido(_pares(csv_tres_megas))


def prueba_los_pesados_no_estan_en_el_repositorio() -> None:
    """No se commitean: si aparecen, alguien metió megabytes al historial."""
    carpeta = Path(__file__).resolve().parents[2] / "datos" / "pruebas"
    grandes = [
        ruta.name
        for ruta in carpeta.iterdir()
        if ruta.is_file() and ruta.stat().st_size > 1024 * 1024
    ]

    assert not grandes, f"estos archivos de prueba no deberían estar aquí: {grandes}"


# --------------------------------------------------------------------------- #
# Los espectros reales: no se versionan, se reproducen
# --------------------------------------------------------------------------- #

RAIZ = Path(__file__).resolve().parents[2]
MANIFIESTO = RAIZ / "herramientas" / "espectros_nist.json"


def prueba_los_espectros_reales_no_se_versionan() -> None:
    """Son de la Coblentz Society y llevan copyright: commitearlos en un repo
    público sería redistribuirlos. Lo que se versiona es el script más el
    manifiesto que los reproduce."""
    reglas = (RAIZ / ".gitignore").read_text(encoding="utf-8")

    assert "datos/referencia/*" in reglas, (
        "datos/referencia/ debe seguir en .gitignore: ahí viven los espectros "
        "con copyright"
    )
    assert MANIFIESTO.is_file(), "falta el manifiesto que los reproduce"
    assert (RAIZ / "herramientas" / "descargar_espectros_nist.py").is_file()


def prueba_el_manifiesto_describe_los_tres_espectros() -> None:
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    espectros = manifiesto["espectros"]

    assert len(espectros) == 3
    for espectro in espectros:
        for llave in (
            "archivo",
            "compuesto",
            "cas",
            "id_nist",
            "indice",
            "fase",
            "puntos",
            "bytes",
            "sha256",
        ):
            assert espectro.get(llave) not in (None, ""), (
                f"a {espectro.get('archivo')} le falta «{llave}»"
            )
        assert len(espectro["sha256"]) == 64


def prueba_los_espectros_de_disco_coinciden_con_el_manifiesto() -> None:
    """Si los archivos están descargados, deben ser los del manifiesto. En un
    clon recién hecho no están, y entonces esta prueba se salta."""
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    carpeta = RAIZ / manifiesto["carpeta_destino"]

    presentes = [
        espectro
        for espectro in manifiesto["espectros"]
        if (carpeta / espectro["archivo"]).is_file()
    ]
    if not presentes:
        pytest.skip(
            "los espectros reales no están descargados; córralos con "
            "«python -m herramientas.descargar_espectros_nist»"
        )

    for espectro in presentes:
        datos = (carpeta / espectro["archivo"]).read_bytes()
        assert len(datos) == espectro["bytes"], espectro["archivo"]
        assert hashlib.sha256(datos).hexdigest() == espectro["sha256"], (
            f"{espectro['archivo']} no es el espectro del manifiesto"
        )


# --------------------------------------------------------------------------- #
# Reproducibles
# --------------------------------------------------------------------------- #


def prueba_regenerar_da_exactamente_los_mismos_bytes(
    carpeta_fixtures: Path, tmp_path: Path
) -> None:
    """El generador es determinista: volver a correrlo no cambia el repositorio,
    y nadie puede editar un archivo de prueba a mano sin que se note."""
    generar(tmp_path)

    diferentes = [
        nombre
        for nombre, _ in generar(tmp_path)
        if (tmp_path / nombre).read_bytes() != (carpeta_fixtures / nombre).read_bytes()
    ]

    assert not diferentes, (
        "estos archivos no coinciden con lo que genera la herramienta; "
        f"regenérelos o revise el cambio: {diferentes}"
    )
