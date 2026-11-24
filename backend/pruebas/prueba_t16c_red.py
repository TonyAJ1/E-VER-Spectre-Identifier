"""T-16a-2 y T-16c: el etiquetado y la red entrenada.

Lo que se comprueba:

- La copia de la red en NumPy hace la misma convolución que una cuenta a mano,
  y si PyTorch está instalado, da lo mismo que la red con que se entrenó.
- El archivo de pesos del repositorio corresponde a esta aplicación: la N de
  la rejilla (D-19), el orden de los grupos de UT-01 y el largo de la ventana.
- La aplicación carga la red por omisión y trabaja en modo híbrido; con
  modelo=None, o sin archivo de pesos, sigue solo con reglas (D-16).
- Las reglas de etiquetado D-24 v2 dan lo que dice la tabla del traspaso.
  Estas necesitan RDKit y se saltan si no está.
"""

from __future__ import annotations

import json
import logging
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.api import RUTA_ANALIZAR, RUTA_PROCESAR, crear_aplicacion
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.configuracion import obtener as obtener_configuracion
from motor_identificacion.inferencia import MODO_HIBRIDO, MODO_REGLAS, motivo_para_solo_reglas
from motor_identificacion.inferencia.red import (
    ARCHIVO_PESOS,
    CONVOLUCIONES,
    ErrorDeModelo,
    _convolucion,
    cargar_red,
)

GRUPOS = tuple(g.id for g in obtener_catalogo().grupos)
hay_pesos = pytest.mark.skipif(not ARCHIVO_PESOS.is_file(), reason="no hay red entrenada")


def _ventana_de(configuracion):
    minimo, maximo = configuracion.validacion.rango_requerido_cm1
    n = configuracion.procesamiento.puntos_rejilla
    inicio, fin = configuracion.procesamiento.rango_rejilla_cm1
    paso = (fin - inicio) / (n - 1)
    return sum(1 for i in range(n) if minimo <= inicio + i * paso <= maximo)


# --- La copia en NumPy ------------------------------------------------------


def prueba_la_convolucion_coincide_con_la_cuenta_a_mano():
    azar = np.random.default_rng(1)
    x = azar.normal(size=(3, 20)).astype(np.float32)
    pesos = azar.normal(size=(4, 3, 5)).astype(np.float32)
    sesgo = azar.normal(size=4).astype(np.float32)
    relleno = 2
    esperado = np.zeros((4, 20), dtype=np.float32)
    rellenado = np.pad(x, ((0, 0), (relleno, relleno)))
    for o in range(4):
        for i in range(20):
            esperado[o, i] = (rellenado[:, i : i + 5] * pesos[o]).sum() + sesgo[o]
    assert np.allclose(_convolucion(x, pesos, sesgo, relleno), esperado, atol=1e-5)


def prueba_sin_archivo_de_pesos_avisa_con_su_propio_error(tmp_path):
    with pytest.raises(ErrorDeModelo):
        cargar_red(tmp_path / "no-existe.npz")


def prueba_un_archivo_con_los_grupos_en_otro_orden_no_se_carga(tmp_path):
    if not ARCHIVO_PESOS.is_file():
        pytest.skip("no hay red entrenada")
    with np.load(ARCHIVO_PESOS, allow_pickle=False) as archivo:
        datos = {k: archivo[k] for k in archivo.files}
    descripcion = json.loads(str(datos["descripcion"]))
    descripcion["grupos"] = list(reversed(descripcion["grupos"]))
    datos["descripcion"] = np.asarray(json.dumps(descripcion))
    ruta = tmp_path / "volteada.npz"
    np.savez(ruta, **datos)
    with pytest.raises(ErrorDeModelo):
        cargar_red(ruta, GRUPOS)


def prueba_la_copia_de_numpy_da_lo_mismo_que_pytorch(tmp_path):
    torch = pytest.importorskip("torch")
    from herramientas.entrenamiento.entrenar import Red

    configuracion = obtener_configuracion()
    largo = _ventana_de(configuracion)
    torch.manual_seed(7)
    red = Red(largo, len(GRUPOS)).eval()
    descripcion = {"grupos": list(GRUPOS), "puntos_rejilla": 1024, "largo_ventana": largo}
    ruta = tmp_path / "red.npz"
    np.savez(
        ruta,
        descripcion=np.asarray(json.dumps(descripcion)),
        **{k: v.detach().numpy() for k, v in red.state_dict().items()},
    )
    copia = cargar_red(ruta, GRUPOS)
    entrada = torch.rand(3, largo)
    with torch.no_grad():
        esperado = torch.sigmoid(red(entrada)).numpy()
    for fila, prob in zip(entrada.numpy(), esperado):
        assert np.allclose(copia.probabilidades(tuple(fila)), prob, atol=1e-5)


# --- El archivo de pesos del repositorio -----------------------------------


@hay_pesos
def prueba_la_red_del_repositorio_corresponde_a_esta_aplicacion():
    configuracion = obtener_configuracion()
    red = cargar_red(grupos_esperados=GRUPOS)
    assert red.grupos == GRUPOS
    assert red.puntos_rejilla == configuracion.procesamiento.puntos_rejilla
    assert red.largo_ventana == _ventana_de(configuracion)
    assert motivo_para_solo_reglas(red, configuracion) is None
    assert {f"{n}.weight" for n, _ in CONVOLUCIONES} <= set(red.pesos)


@hay_pesos
def prueba_la_red_da_siete_probabilidades_entre_cero_y_uno():
    red = cargar_red(grupos_esperados=GRUPOS)
    for valor in (0.0, 0.5, 1.0):
        salida = red.probabilidades((valor,) * red.largo_ventana)
        assert len(salida) == len(GRUPOS)
        assert all(0.0 <= p <= 1.0 for p in salida)


@hay_pesos
def prueba_una_ventana_de_otro_largo_se_rechaza():
    red = cargar_red(grupos_esperados=GRUPOS)
    with pytest.raises(ErrorDeModelo):
        red.probabilidades((0.5,) * (red.largo_ventana - 1))


# --- La aplicación ---------------------------------------------------------


def _analizar(cliente, configuracion=None):
    """Una cetona sintética por /api/procesar y luego por /api/analizar."""
    filas = ["numero_de_onda,absorbancia"]
    onda = 4000.0
    while onda >= 400:
        valor = 0.02 + math.exp(-((onda - 1715) ** 2) / (2 * 8.5**2))
        filas.append(f"{onda:.1f},{valor:.6f}")
        onda -= 2
    contenido = "\n".join(filas).encode("utf-8")
    procesado = cliente.post(
        RUTA_PROCESAR, files={"archivo": ("cetona.csv", contenido, "text/csv")}
    ).json()
    assert procesado["valido"], procesado
    return cliente.post(RUTA_ANALIZAR, json=procesado["espectro"]).json()


@hay_pesos
def prueba_la_aplicacion_carga_la_red_por_omision(caplog):
    configuracion = obtener_configuracion()
    with caplog.at_level(logging.INFO):
        cliente = TestClient(crear_aplicacion())
    assert _analizar(cliente, configuracion)["modo"] == MODO_HIBRIDO
    assert any("modo=hibrido" in r.getMessage() for r in caplog.records)


def prueba_con_modelo_none_la_aplicacion_trabaja_solo_con_reglas():
    configuracion = obtener_configuracion()
    cliente = TestClient(crear_aplicacion(modelo=None))
    assert _analizar(cliente, configuracion)["modo"] == MODO_REGLAS


def prueba_sin_archivo_de_pesos_la_aplicacion_arranca_en_modo_reglas(monkeypatch, tmp_path, caplog):
    import motor_identificacion.inferencia.red as red

    monkeypatch.setattr(red, "ARCHIVO_PESOS", tmp_path / "no-existe.npz")
    monkeypatch.setattr(red.cargar_red, "__defaults__", (tmp_path / "no-existe.npz", None))
    configuracion = obtener_configuracion()
    with caplog.at_level(logging.INFO):
        cliente = TestClient(crear_aplicacion())
    assert _analizar(cliente, configuracion)["modo"] == MODO_REGLAS
    assert any("red no cargada" in r.getMessage() for r in caplog.records)


# --- El etiquetado (T-16a-2) -----------------------------------------------


@pytest.mark.parametrize(
    ("smiles", "esperado"),
    [
        # Ácido benzoico: O-H y C=O los dos, y anillo (propuesta v2.6).
        ("OC(=O)c1ccccc1", {"GF-01": "1", "GF-05": "1", "GF-07": "1", "GF-03": "0"}),
        # Amida primaria: N-H y C=O; no activa GF-06 (D-24 v2).
        ("CC(N)=O", {"GF-02": "1", "GF-05": "1", "GF-06": "0"}),
        # Amina terciaria: sin N-H.
        ("CN(C)C", {"GF-02": "0", "GF-03": "1"}),
        # Benzonitrilo.
        ("N#Cc1ccccc1", {"GF-04": "1", "GF-07": "1"}),
        # Alquino interno sin nitrilo: GF-04 se enmascara.
        ("CC#CC", {"GF-04": "x"}),
        # Alquino terminal: GF-02 se enmascara (marginal sin decidir).
        ("C#CCCC", {"GF-02": "x"}),
        # Nitrobenceno: el nitro no quita el anillo.
        ("[O-][N+](=O)c1ccccc1", {"GF-07": "1", "GF-02": "0"}),
        # Benzaldehído: el aldehído no activa GF-03.
        ("O=Cc1ccccc1", {"GF-03": "0", "GF-05": "1"}),
        # Oxima: GF-01 se enmascara; la imina enmascara GF-06.
        ("CC=NO", {"GF-01": "x", "GF-06": "x"}),
        # Piridina: heteroaromático, GF-07 se enmascara.
        ("c1ccncc1", {"GF-07": "x"}),
        # Alqueno con =C-H.
        ("C=CCCCC", {"GF-06": "1"}),
    ],
)
def prueba_el_etiquetado_sigue_la_tabla_de_d24(smiles, esperado):
    pytest.importorskip("rdkit")
    from herramientas.dataset.etiquetar import etiquetas_de

    celdas, _ = etiquetas_de(smiles)
    assert celdas is not None
    for grupo, valor in esperado.items():
        assert celdas[grupo] == valor, (smiles, grupo)


def prueba_un_complejo_metalico_se_excluye_entero():
    pytest.importorskip("rdkit")
    from herramientas.dataset.etiquetar import etiquetas_de

    celdas, motivo = etiquetas_de("[Fe].c1ccccc1")
    assert celdas is None
    assert "Fe" in motivo
