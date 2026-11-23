# Modelo de MOD-06

Aquí van los pesos de la red convolucional de una dimensión cuando el equipo la entrene (tarea T-16).

Hoy la carpeta no tiene pesos. Para entrenar el modelo hacen falta espectros infrarrojos reales de SDBS o NIST, cada uno etiquetado con los grupos que tiene su molécula en un vector de siete posiciones. Hay que pasarlos por MOD-04 para que tengan el mismo rango, la misma rejilla y la misma normalización que los que verá el motor, y separarlos en 70, 15 y 15 por ciento para entrenamiento, validación y prueba, sin que un compuesto quede en dos conjuntos. La meta de RNF-08 es una F1 de al menos 0.80 en los grupos bien marcados, medida en el conjunto de prueba.

Mientras no exista el modelo se aplica el plan B del diseño de MOD-06: en UT-03 el peso de las reglas es 1 y el del modelo es 0, y la aplicación funciona solo con la vía de reglas sin cambiar el contrato.
