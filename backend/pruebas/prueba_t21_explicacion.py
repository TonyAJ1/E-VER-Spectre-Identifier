"""Pruebas de T-21: la explicación de cada grupo detectado.

CA-07.1: con un C=O detectado en 1715 cm⁻¹, la explicación indica la región
característica (de 1670 a 1780 cm⁻¹), la posición observada, el rasgo que lo
delata (pico intenso y agudo) y por qué corresponde al carbonilo.

CA-07.2: con un N–H detectado en la zona que comparte con O–H, la
explicación dice por qué se atribuyó a N–H y no a O–H: la banda es más
angosta.
"""

from __future__ import annotations

from backend.educativo.explicador import explicar
from backend.pruebas.apoyo_navegador import subir_en_la_pagina
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.catalogo import obtener_plantillas
from motor_identificacion.pruebas import espectros_simulados as sim


def _deteccion(grupo: str, pico: float | None) -> dict:
    region = list(obtener_catalogo().grupo(grupo).region_cm1)
    return {"grupo": grupo, "confianza": 0.94, "region_cm1": region, "pico_cm1": pico}


def prueba_ca_07_1_la_explicacion_del_c_o_trae_sus_cuatro_partes() -> None:
    explicacion = explicar(_deteccion("GF-05", 1715.0), obtener_catalogo(), obtener_plantillas())

    assert explicacion["region"] == "de 1670 a 1780 cm⁻¹"
    assert explicacion["posicion"] == "1715 cm⁻¹"
    assert "intenso y agudo" in explicacion["rasgo"]
    assert "carbonilo" in explicacion["por_que"]


def prueba_ca_07_2_la_del_n_h_dice_por_que_no_es_o_h() -> None:
    explicacion = explicar(_deteccion("GF-02", 3360.0), obtener_catalogo(), obtener_plantillas())

    texto = explicacion["por_que"]
    assert "N–H y no a O–H" in texto
    assert "angosta" in texto


def prueba_la_region_sale_del_catalogo_y_no_de_la_plantilla() -> None:
    deteccion = _deteccion("GF-05", 1715.0)
    deteccion["region_cm1"] = [1000.0, 2000.0]

    explicacion = explicar(deteccion, obtener_catalogo(), obtener_plantillas())

    assert explicacion["region"] == "de 1000 a 2000 cm⁻¹"


def prueba_en_la_pagina_se_abre_la_explicacion_del_c_o(
    pagina, servidor: str, tmp_path, evidencia
) -> None:
    eje, intensidad = sim.espectro(sim.CETONA)
    ruta = tmp_path / "cetona.csv"
    filas = ["numero de onda,absorbancia"] + [
        f"{x:.4f},{y:.6f}" for x, y in zip(eje, intensidad)
    ]
    ruta.write_text("\n".join(filas) + "\n", encoding="ascii")
    subir_en_la_pagina(pagina, servidor, ruta, "cetona.csv")
    pagina.click("#boton-analizar")
    pagina.wait_for_function(
        "document.getElementById('analisis').dataset.estado === 'detecciones'"
    )

    carbonilo = pagina.locator('.deteccion[data-grupo="GF-05"]')
    carbonilo.locator("summary").click()

    texto = carbonilo.locator(".explicacion").inner_text()
    assert "Región característica" in texto and "de 1670 a 1780 cm⁻¹" in texto
    assert "Pico observado" in texto
    assert "Lo que lo delata" in texto
    assert "Por qué corresponde a este grupo" in texto
    evidencia(pagina, "t21-ca-07-1-explicacion")
