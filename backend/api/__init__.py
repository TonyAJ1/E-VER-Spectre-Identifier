"""Orquestación HTTP del backend (T-07).

El punto de entrada es `backend.api.aplicacion:app`. Este `__init__` no lo
importa a propósito: crear la aplicación carga UT-03, y eso debe ocurrir al
arrancar el servidor, no al importar cualquier cosa del paquete.
"""
