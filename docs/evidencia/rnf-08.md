# RNF-08 · evaluación de la vía ML y del motor completo (T-16d)

Corrida única el 24/11/2026 con `python -m herramientas.entrenamiento.evaluar`.

| | |
|---|---|
| Conjunto de prueba | 285 espectros de 265 compuestos (Chemotion IR) |
| SHA-256 de `split-prueba.txt` | `5f70ecbbd246c84af584a23cbb0f3a0e15f90a971694993959f840f6675d017a` |
| Semilla del entrenamiento | 20261124 |
| Época elegida (por validación) | 62 |
| Umbral del motor (UT-03) | 60 % |
| Pesos de la fusión (UT-03) | reglas 0.5, ML 0.5 |
| Etiquetado | D-24 v2 provisional (ver herramientas/dataset/etiquetar.py) |
| Support mínimo para decidir | 20 positivos (PROVISIONAL) |
| Tiempo del motor completo por espectro | promedio 20 ms, máximo 62 ms (RNF-02 pide menos de 5 s) |

Las celdas enmascaradas (la x de `conjunto.csv`) no cuentan en ninguna tabla.

## Puerta de D-13 (F1 de al menos 0.80 en GF-01, GF-04 y GF-05)

**Vía ML sola:**

- GF-01 O–H (alcoholes, fenoles y ácidos): F1 0.747, no pasa
- GF-04 C≡N (nitrilos): F1 0.867, sin decidir (support 14 < 20)
- GF-05 C=O (carbonilo): F1 0.933, pasa

**Motor completo:**

- GF-01 O–H (alcoholes, fenoles y ácidos): F1 0.635, no pasa
- GF-04 C≡N (nitrilos): F1 0.867, sin decidir (support 14 < 20)
- GF-05 C=O (carbonilo): F1 0.868, pasa

## Tablas

### 1. Vía ML sola, corte en 0.5

| Grupo | Precisión | Recall | F1 | Support | Celdas | VP | FP | FN | VN |
|---|---|---|---|---|---|---|---|---|---|
| GF-01 O–H (alcoholes, fenoles y ácidos) | 0.674 | 0.838 | 0.747 | 37 | 283 | 31 | 15 | 6 | 231 |
| GF-02 N–H (aminas y amidas) | 0.932 | 0.943 | 0.937 | 87 | 278 | 82 | 6 | 5 | 185 |
| GF-03 C–H alifático (sp³) | 0.934 | 0.972 | 0.952 | 247 | 285 | 240 | 17 | 7 | 21 |
| GF-04 C≡N (nitrilos) | 0.812 | 0.929 | 0.867 | 14 | 276 | 13 | 3 | 1 | 259 |
| GF-05 C=O (carbonilo) | 0.912 | 0.954 | 0.933 | 131 | 285 | 125 | 12 | 6 | 142 |
| GF-06 C=C (alquenos) | 0.448 | 0.833 | 0.583 | 36 | 262 | 30 | 37 | 6 | 189 |
| GF-07 Anillo aromático | 0.965 | 0.996 | 0.980 | 247 | 267 | 246 | 9 | 1 | 11 |

Macro F1: **0.857**

### 2. Motor completo, fusión y umbral de 60 %

| Grupo | Precisión | Recall | F1 | Support | Celdas | VP | FP | FN | VN |
|---|---|---|---|---|---|---|---|---|---|
| GF-01 O–H (alcoholes, fenoles y ácidos) | 0.562 | 0.730 | 0.635 | 37 | 283 | 27 | 21 | 10 | 225 |
| GF-02 N–H (aminas y amidas) | 0.969 | 0.713 | 0.821 | 87 | 278 | 62 | 2 | 25 | 189 |
| GF-03 C–H alifático (sp³) | 0.909 | 0.968 | 0.937 | 247 | 285 | 239 | 24 | 8 | 14 |
| GF-04 C≡N (nitrilos) | 0.812 | 0.929 | 0.867 | 14 | 276 | 13 | 3 | 1 | 259 |
| GF-05 C=O (carbonilo) | 0.813 | 0.931 | 0.868 | 131 | 285 | 122 | 28 | 9 | 126 |
| GF-06 C=C (alquenos) | 0.354 | 0.472 | 0.405 | 36 | 262 | 17 | 31 | 19 | 195 |
| GF-07 Anillo aromático | 0.984 | 0.725 | 0.834 | 247 | 267 | 179 | 3 | 68 | 17 |

Macro F1: **0.767**

### 3. Vía de reglas sola, mismo umbral (contexto)

| Grupo | Precisión | Recall | F1 | Support | Celdas | VP | FP | FN | VN |
|---|---|---|---|---|---|---|---|---|---|
| GF-01 O–H (alcoholes, fenoles y ácidos) | 0.267 | 0.757 | 0.394 | 37 | 283 | 28 | 77 | 9 | 169 |
| GF-02 N–H (aminas y amidas) | 0.476 | 0.690 | 0.563 | 87 | 278 | 60 | 66 | 27 | 125 |
| GF-03 C–H alifático (sp³) | 0.883 | 0.976 | 0.927 | 247 | 285 | 241 | 32 | 6 | 6 |
| GF-04 C≡N (nitrilos) | 0.071 | 1.000 | 0.133 | 14 | 276 | 14 | 183 | 0 | 79 |
| GF-05 C=O (carbonilo) | 0.639 | 0.931 | 0.758 | 131 | 285 | 122 | 69 | 9 | 85 |
| GF-06 C=C (alquenos) | 0.179 | 0.556 | 0.270 | 36 | 262 | 20 | 92 | 16 | 134 |
| GF-07 Anillo aromático | 0.982 | 0.668 | 0.795 | 247 | 267 | 165 | 3 | 82 | 17 |

Macro F1: **0.549**

### 4. Predictor que siempre dice que sí (contexto)

| Grupo | Precisión | Recall | F1 | Support | Celdas | VP | FP | FN | VN |
|---|---|---|---|---|---|---|---|---|---|
| GF-01 O–H (alcoholes, fenoles y ácidos) | 0.131 | 1.000 | 0.231 | 37 | 283 | 37 | 246 | 0 | 0 |
| GF-02 N–H (aminas y amidas) | 0.313 | 1.000 | 0.477 | 87 | 278 | 87 | 191 | 0 | 0 |
| GF-03 C–H alifático (sp³) | 0.867 | 1.000 | 0.929 | 247 | 285 | 247 | 38 | 0 | 0 |
| GF-04 C≡N (nitrilos) | 0.051 | 1.000 | 0.097 | 14 | 276 | 14 | 262 | 0 | 0 |
| GF-05 C=O (carbonilo) | 0.460 | 1.000 | 0.630 | 131 | 285 | 131 | 154 | 0 | 0 |
| GF-06 C=C (alquenos) | 0.137 | 1.000 | 0.242 | 36 | 262 | 36 | 226 | 0 | 0 |
| GF-07 Anillo aromático | 0.925 | 1.000 | 0.961 | 247 | 267 | 247 | 20 | 0 | 0 |

Macro F1: **0.509**

## Lectura

Esta sección se escribió después de la corrida y no cambia ningún número de arriba.

- La red sola saca un macro F1 de 0.857 y la vía de reglas sola 0.549. El motor completo, con la fusión a partes iguales de UT-03, queda en 0.767: la fusión baja el resultado de la red en casi todos los grupos, sobre todo en GF-07, GF-02 y GF-06, donde las reglas tienen poco recall o muchos falsos positivos.
- En la puerta, GF-05 pasa con la red sola y con el motor completo. GF-01 no pasa en ninguno de los dos (0.747 y 0.635). GF-04 da 0.867, pero con 14 positivos en prueba queda sin decidir.
- GF-03 y GF-07 son casi todo positivos en este conjunto: el predictor que siempre dice que sí ya saca 0.929 y 0.961. Sus F1 no dicen mucho de lo que la red aprendió.
- Según D-13 y D-16 esto lo decide el equipo junto y por escrito: si se recalibran los pesos de la fusión con el conjunto de validación (D-15) y si GF-01 activa algo del plan B. No se movió ningún peso ni umbral para escribir este documento.
- Todo el etiquetado sigue D-24 v2 tal como está en el traspaso, sin firmar. Si el equipo cambia el criterio, hay que volver a etiquetar, entrenar y evaluar con un conjunto de prueba nuevo, porque este ya se usó.
