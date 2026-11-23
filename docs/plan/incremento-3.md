# Incremento 3: identificar grupos funcionales

Este archivo resume cómo se trabajó el incremento 3, tareas T-14 a T-19. Al terminar, quien sube un espectro válido puede pulsar «Analizar» y ver qué grupos funcionales tiene, cada uno con su confianza en porcentaje y de mayor a menor.

## Cómo quedó

El catálogo de los 7 grupos vive en `datos/catalogo/grupos.json` y lo lee UT-01 en `backend/utilerias/catalogo/`. Trae la región de cada grupo, su rasgo y un bloque `regla` con lo que necesita la vía de reglas.

MOD-06 vive en `motor_identificacion/`, ya con guion bajo como decía D-7. No importa nada del backend: recibe el eje, la intensidad normalizada y los grupos del catálogo, y devuelve el resultado con el contrato de la sección 5 de su diseño. Sus pruebas están en `motor_identificacion/pruebas/` y pytest ya las recorre.

La página llama a la ruta nueva `POST /api/analizar` con el eje y la intensidad que el servidor le devolvió al validar el archivo. El archivo no se vuelve a subir, así MOD-06 queda aislado y el servidor no guarda nada entre peticiones.

## Plan B del modelo (T-16)

No hay un conjunto de espectros etiquetados para entrenar la red, así que no se entrenó ni se inventaron pesos. Se aplica el plan B del diseño de MOD-06: en UT-03 el peso de las reglas es 1 y el del modelo es 0. La tarea T-16 sigue abierta; en `motor_identificacion/modelo/LEEME.md` está lo que falta. Cuando exista el modelo, basta con subir el peso en UT-03 y conectar la carga en `via_ml.py`.

## Supuestos que el equipo debe revisar

Los números del bloque `regla` del catálogo son SUPUESTOS iniciales: la prominencia que se espera de cada grupo, el ancho que separa una banda de O–H de una de N–H (150 cm⁻¹) y la prominencia de la banda de C–H que acompaña al alqueno y al aromático. En `via_reglas.py` también hay tres números de trabajo: un margen de 20 cm⁻¹ alrededor de cada región, una relación señal a ruido de 10 y un tope de 0.5 para un grupo al que le falta su banda acompañante.

Todo se probó con espectros simulados. Las pruebas de CA-05.1 (acetona) y CA-05.2 (ácido benzoico) con los espectros reales de NIST no se pudieron correr en la nube porque la red bloquea NIST. Se saltan solas y hay que correrlas en una computadora del equipo después de `python -m herramientas.descargar_espectros_nist`. Si fallan, lo que hay que ajustar son los números del bloque `regla`, no el código.

## Mensajes nuevos de UT-02

`SIN_DETECCIONES` dice «No se encontraron detecciones confiables» y sugiere revisar la calidad del espectro. `ANALISIS_FALLIDO` dice «No fue posible completar el análisis; intenta de nuevo», que es el texto de CA-05.4.
