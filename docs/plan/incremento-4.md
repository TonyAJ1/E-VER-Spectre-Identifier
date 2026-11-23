# Incremento 4: capa educativa, explicar y resaltar

Este archivo resume cómo se trabajó el incremento 4, tareas T-20 a T-24. Al terminar, cada grupo detectado trae su explicación y se puede resaltar en la gráfica.

## Cómo quedó

Las plantillas de explicación viven en `datos/catalogo/plantillas.json` y las lee UT-01. Cada plantilla solo explica por qué el pico corresponde a su grupo. La región y el rasgo no se escriben en la plantilla: MOD-07 los toma del catálogo, para que los números vivan en un solo lugar, y una prueba lo revisa.

MOD-07 vive en `backend/educativo/explicador.py`. Junta la región, el pico observado, el rasgo y el porqué, y la ruta del análisis agrega esa explicación a cada grupo. Si un grupo no tiene plantilla, dice «Explicación no disponible», deja el error en el registro y los demás grupos siguen igual.

En la página, cada grupo tiene el botón «Resaltar en la gráfica». El visor pinta una franja con el color del grupo sobre su región y una línea punteada en el pico. Debajo de la gráfica aparece una leyenda con los grupos resaltados. Si el motor no dio la posición del pico, se resalta la región completa y la leyenda lo avisa. El resaltado es un complemento pequeño escrito en `visor.js`, sin agregar otra librería.

## Lo que falta del equipo

Las siete plantillas son un borrador escrito con ayuda de IA. El plan pide que cada una se compare contra la tabla de la University of Colorado Boulder y contra LibreTexts, que la apruebe quien no la escribió y, si se puede, que la revise un profesor de química. Cada plantilla trae sus fuentes y el campo `revisado_por`, hoy vacío, para registrar esa revisión.
