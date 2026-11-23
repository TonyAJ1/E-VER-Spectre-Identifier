# Archivos de prueba del incremento 1 (T-0R)

Todos los archivos de esta carpeta están **fabricados**: no contienen una sola línea de datos
de NIST ni de la Coblentz Society. El incremento 1 solo valida **estructura, tamaño, puntos y
rango** —nunca mira química real—, así que un espectro sintético cubre todas sus CA, evita el
problema de redistribución del repositorio público y deja que cualquiera corra las pruebas sin
descargar nada.

Los espectros **reales** (acetona, ácido benzoico y anilina) viven en `datos/referencia/`, que
está en `.gitignore`. Se reproducen con `herramientas/descargar_espectros_nist.py` y su
manifiesto. Hacen falta a partir del incremento 2.

## Cómo se regeneran

Desde la raíz del repositorio:

```bash
python -m herramientas.generar_fixtures
```

El generador es **determinista**: vuelve a escribir exactamente los mismos bytes, así que
`git status` queda limpio si nadie tocó la herramienta. Una prueba lo comprueba
(`prueba_regenerar_da_exactamente_los_mismos_bytes`), de modo que un archivo editado a mano se
delata.

## Los archivos

| Archivo | Qué es | CA |
|---|---|---|
| `espectro-valido.jdx` | `.jdx` válido: etiquetas obligatorias de UT-03, `##TITLE=` en la primera línea, `##END=` en la última, `##XYDATA=` con 900 pares de 400 a 4000 cm⁻¹ | CA-01.1 |
| `espectro-valido-900-puntos.csv` | CSV de dos columnas, 900 puntos, 400–4000 cm⁻¹ | CA-02.1 |
| `espectro-puntos-minimos.csv` | CSV con **exactamente** los puntos mínimos de UT-03 (hoy 300), cubriendo el rango requerido: la mitad que debe aceptarse | CA-02.6 |
| `espectro-un-punto-menos.csv` | CSV con **un punto menos** que el mínimo (hoy 299). Cubre el rango de sobra, para que el conteo sea la única razón posible de rechazo | CA-02.6 |
| `espectro-rango-corto.csv` | CSV de 900 puntos que arranca en 1500 cm⁻¹: no alcanza el extremo inferior del rango requerido. Puntos de sobra, así que el rango es la única razón de rechazo | CA-02.3 |
| `espectro-truncado.jdx` | `.jdx` cortado: tiene `##TITLE=` y `##XYDATA=`, le falta `##END=` | CA-02.4 |
| `espectro-comprimido.jdx` | Los mismos 900 puntos de `espectro-valido.jdx`, guardados en la forma comprimida DIFDUP con XFACTOR y YFACTOR, que es como vienen los archivos de las bases públicas. Sirve para probar la descompresión de MOD-04 sin copiar datos reales | T-08 |
| `espectro-factores.jdx` | Los mismos 900 puntos con la intensidad multiplicada por mil y `##YFACTOR=0.001`. Si MOD-04 no aplica el factor, los valores salen mil veces más grandes | T-08 |
| `archivo-vacio.csv` | 0 bytes | CA-02.4 |
| `binario-disfrazado.csv` | Bytes binarios con cabecera `MZ` y bytes nulos, con extensión admitida. **No es un ejecutable**: no tiene cabecera PE válida ni una sola instrucción. El rechazo debe venir del contenido, no de la extensión | CA-02.5 |
| `imagen.png` | PNG válido de 1×1 píxel: un formato que la aplicación no admite | CA-01.3 |

## Los que no están aquí

Estos tres **no se commitean** —no conviene meter megabytes al historial de git— y los genera la
suite de pruebas al arrancar, en la carpeta temporal de pytest
([conftest.py](../../backend/pruebas/conftest.py)):

| Archivo | Qué es | CA |
|---|---|---|
| `espectro-tamano-maximo.csv` | CSV válido de **exactamente** el tamaño máximo de UT-03 (hoy 5 242 880 bytes), con puntos y rango suficientes | CA-01.2 |
| `espectro-un-byte-de-mas.csv` | El anterior más un byte | CA-02.2 |
| `espectro-tres-megas.csv` | CSV válido de ~3 MB: pasa de 1 MB, que es cuando FastAPI escribe el archivo temporal en disco | RNF-09 |

El tamaño sale de UT-03, no de un número escrito en el código: si el equipo cambia el límite,
CA-01.2 y CA-02.2 siguen probando el límite de verdad. Para tenerlos a mano en una evidencia:

```bash
python -m herramientas.generar_fixtures --grandes <carpeta fuera del repositorio>
```
