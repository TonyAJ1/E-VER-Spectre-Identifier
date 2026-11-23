# Incremento 5: reporte PDF

Este archivo resume cómo se trabajó el incremento 5, tareas T-25 a T-27. Al terminar, la persona que analizó un espectro puede descargar un reporte en PDF con el nombre del archivo, la fecha y hora, la gráfica con las regiones resaltadas, cada grupo con su confianza y su explicación, y el aviso de que el resultado es orientativo.

## Decisión tomada al empezar

**D-3, librería de PDF.** Se usa reportlab 4.2.5, con licencia BSD. Arma el PDF en memoria, sin escribir en disco, lo que cuida RNF-09, y no necesita programas instalados fuera de Python. Para que los acentos, la eñe y el símbolo cm⁻¹ se vean bien se guardaron en el repositorio las fuentes DejaVu, de licencia libre, en `backend/reportes/fuentes/`. Las pruebas leen el texto del PDF con pypdf 5.1.0. Es una decisión provisional como las del incremento 2; si el equipo la cambia, hay que registrarlo en la bitácora.

## Cómo quedó

La página pide el reporte a `POST /api/reporte` y manda en JSON el nombre del archivo, la fecha y hora local del análisis, las detecciones y la gráfica como imagen PNG. El servidor no guardó nada del análisis, por eso la página tiene que mandarlo. Lo que no se toma de la página son los textos: los nombres de los grupos y las explicaciones se vuelven a armar con el catálogo de UT-01 y con MOD-07, de modo que el PDF dice lo mismo que el sistema aunque alguien altere la petición.

MOD-08 vive en `backend/reportes/generador.py`. Los grupos van de mayor a menor confianza y el aviso orientativo sale de UT-02. La respuesta llega como descarga con el nombre `reporte_analisis.pdf`.

La gráfica del reporte la dibuja la página con la misma librería de MOD-05, en un lienzo aparte con fondo blanco y con todos los grupos detectados resaltados, no solo los que el usuario marcó. El servidor revisa que la imagen sea un PNG de verdad y de tamaño razonable antes de ponerla en el PDF. Si no llega, el reporte lo dice en lugar de dejar un hueco.

Si el análisis no encontró nada confiable, el botón del reporte también aparece y el PDF lo dice con el mismo aviso de UT-02 que se ve en pantalla. Si la petición no sirve la API contesta 400, y si MOD-08 falla contesta 500. En los dos casos llega el mensaje REPORTE_FALLIDO de UT-02, sin detalles técnicos. La página lo muestra, deja los resultados en pantalla y permite volver a pedir el reporte.

## Supuestos que el equipo debe revisar

El tope de la imagen de la gráfica es de 4 MB. No es un parámetro de negocio, solo evita cuerpos absurdos, por eso no está en UT-03. Lo mismo pasa con el largo máximo del nombre del archivo en el reporte, de 255 caracteres.

La fecha y hora que lleva el reporte es la de la computadora de la persona en el momento en que terminó el análisis, no la del servidor.

## Prueba de punta a punta

T-27 cierra con una prueba que recorre toda la aplicación en el navegador: sube un archivo, ve la gráfica, analiza, abre la explicación, resalta un grupo y descarga el reporte. Corre con espectros simulados, porque desde la nube no se pueden descargar los de NIST.
