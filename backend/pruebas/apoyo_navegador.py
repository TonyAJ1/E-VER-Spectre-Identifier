"""Ayudas para las pruebas que usan el navegador (incremento 2)."""

from __future__ import annotations

from pathlib import Path


def subir_en_la_pagina(pagina, base: str, ruta: Path, nombre: str) -> None:
    """Abre la página, elige el archivo, pulsa Validar y espera el veredicto."""
    pagina.goto(base + "/")
    pagina.set_input_files(
        "#archivo",
        files=[{"name": nombre, "mimeType": "application/octet-stream",
                "buffer": ruta.read_bytes()}],
    )
    pagina.click("#boton-validar")
    pagina.wait_for_function(
        "['aceptado','rechazado','error'].includes("
        "document.getElementById('resultado').dataset.estado)"
    )


def marcas(pagina) -> list:
    return pagina.evaluate(
        "window.EVER.visor.marcas(document.getElementById('grafica-lienzo'))"
    )


def color_en(pagina, onda: float) -> list:
    """El color del pixel de la gráfica en ese número de onda, cerca de la
    base, donde no pasa la línea del espectro."""
    return pagina.evaluate(
        """(onda) => {
            const g = window.EVER.visor.grafica(document.getElementById('grafica-lienzo'));
            const x = Math.round(g.scales.x.getPixelForValue(onda) * devicePixelRatio);
            const y = Math.round((g.chartArea.bottom - 20) * devicePixelRatio);
            return Array.from(g.ctx.getImageData(x, y, 1, 1).data);
        }""",
        onda,
    )
