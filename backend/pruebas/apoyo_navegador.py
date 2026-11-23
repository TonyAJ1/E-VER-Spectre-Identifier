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
