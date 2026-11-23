# Incremento 2: procesar y ver el espectro

Este archivo resume cómo se trabajó el incremento 2 y qué decisiones se tomaron al empezarlo. Las tareas son de la T-08 a la T-13 del Plan de Implementación. Al terminar, la persona que sube un espectro válido ya ve su gráfica en pantalla.

## Orden de trabajo

Primero va la cadena de MOD-04 en orden estricto, porque cada paso usa lo que deja el anterior. T-08 lee el archivo y saca los pares de número de onda e intensidad. T-09 ordena esos pares y pasa la transmitancia a absorbancia. T-10 normaliza la intensidad entre 0 y 1 y la acomoda en una rejilla fija. T-11 cubre el caso de la línea plana. Después viene la gráfica de MOD-05: T-12 la dibuja con el eje invertido y T-13 la hace caber en un celular y evita que aparezca vacía cuando el archivo no pasa.

## Decisiones tomadas al empezar

Las tres quedaron como decisiones provisionales el 23 de noviembre de 2026, porque el equipo pidió avanzar sin esperar. Se pueden cambiar; si alguna cambia, hay que registrarlo en la bitácora.

**D-2, lector de espectro.** MOD-03 se queda con su lectura ligera, que solo revisa el encabezado y cuenta filas, y la lectura completa vive dentro de MOD-04 en `backend/preprocesamiento/lector.py`. Así lo pide también la tabla de utilerías de los Requerimientos, que pone los lectores de JCAMP-DX y CSV dentro de MOD-04. No se tocó el código de MOD-03.

**D-1, librería de gráficas.** Se usa Chart.js 4.4.7, con licencia MIT. Funciona con JavaScript puro, invierte el eje, se adapta al ancho de la pantalla, tiene un complemento para marcar regiones que servirá en el incremento 4 y puede sacar la gráfica como imagen para el PDF del incremento 5. El archivo de la librería se guardó dentro del repositorio, en `frontend/visor-espectro/libreria/`, para que la aplicación no dependa de internet.

**Tamaño de la rejilla.** El diseño de MOD-06 solo da 1024 puntos como ejemplo, así que es un SUPUESTO que el equipo debe confirmar. El valor vive en UT-03 como `procesamiento.puntos_rejilla`, junto con el rango del eje en `procesamiento.rango_rejilla_cm1`, que va de 400 a 4000.

## Supuestos que el equipo debe revisar

Un CSV no dice en qué unidad viene la intensidad. Si trae encabezado, se busca ahí la palabra absorbancia o transmitancia. Si no lo trae, se decide por los valores: si alguno pasa de 1.5 se toma como transmitancia en porcentaje; si todos están entre 0 y 1 y la mitad o más pasan de 0.5 se toma como transmitancia en fracción; en otro caso se toma como absorbancia. Es un SUPUESTO.

En un JCAMP-DX en transmitancia, si algún valor pasa de 1.5 se entiende que viene en porcentaje. También es un SUPUESTO.

Una transmitancia de cero o negativa no tiene logaritmo. Se sube a una millonésima antes de convertir, para que el cálculo no falle.

Fuera del tramo que de verdad midió el archivo no hay datos. En esos puntos de la rejilla la intensidad queda en cero y la respuesta dice cuál fue el tramo medido, de modo que la gráfica solo dibuja lo que sí se midió y no inventa valores.

El diseño de MOD-06 menciona una corrección de línea base. En este incremento solo se hace la normalización entre 0 y 1 que pide T-10; una corrección más fina se puede discutir en el incremento 3 si el motor la necesita.

## Cambio en la respuesta de la API

La ruta `POST /api/validar` sigue igual, pero cuando el archivo se acepta la respuesta trae un dato más, `espectro`, con el eje, la intensidad normalizada, el tramo medido y la unidad original. No se creó otra ruta porque el archivo no se guarda en ningún lado (RNF-09): todo se procesa en la misma petición en que se sube. Si el archivo pasa la validación pero sus datos no se pueden leer, o si es una línea plana, la respuesta es un rechazo normal con su mensaje de UT-02.

## Espectros reales de NIST

Desde la nube no se pudo descargar nada de NIST porque la red lo bloquea. La prueba de T-08 con el archivo real se salta sola cuando el archivo no está en `datos/referencia/`. Para correrla hay que bajar los espectros en una computadora del equipo con `python -m herramientas.descargar_espectros_nist` y volver a lanzar las pruebas.
