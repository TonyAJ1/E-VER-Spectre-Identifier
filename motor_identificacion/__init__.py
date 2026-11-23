"""MOD-06, motor de identificación de grupos funcionales.

Es una zona aislada: no importa nada del backend, no abre archivos y no usa la
red. Solo recibe el eje y el vector de intensidad que deja MOD-04, más los
datos del catálogo y los parámetros que le pasa quien lo llama, y devuelve las
detecciones con el contrato de la sección 5 del diseño de MOD-06.
"""
