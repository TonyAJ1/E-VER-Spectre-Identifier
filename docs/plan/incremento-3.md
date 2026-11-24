# Incremento 3 (C) — Identificar grupos funcionales

**Proyecto:** E-VER Spectre Identifier · **Equipo:** E-VER (Electronic-Versions) — Sergio Uriel Bustamante Bustos, Julio Antonio Jiménez Jiménez
**Módulos nuevos:** MOD-06 (Motor de identificación) y UT-01 (Catálogo de grupos funcionales)
**RF / HU:** RF-04 / HU-05 y RF-07 / HU-08 · **RNF:** RNF-08 (calidad del motor), RNF-02 (≤ 5 s), RNF-04 (modularidad)
**Criterios de aceptación:** CA-05.1 … CA-05.4 y CA-08.1 … CA-08.3
**Tareas del Plan V3:** T-14 … T-19 (más T-3R, de datos)
**Hitos:** H8 → H9 → H10
**Depende de:** Incremento 2 cerrado (H7) — MOD-04 entrega el espectro normalizado
**Versión de este plan:** 2.5 (24/11/2026) · **Estado:** T-14, T-15a y T-15b implementados. **H8 sigue ABIERTO**: la vía de reglas funciona pero su puntaje solo acierta 1 de 8 conjuntos completos sobre espectros reales — ver **D-21**, que abre tres frentes. **D-12 opción B resuelta** (Chemotion IR, 4 183 espectros): T-16 ya no está bloqueado y debe arrancar **en paralelo**, sin esperar a que se cierre H8.

*(Historial: 1.0 decisiones abiertas · 1.1–1.4 cierre de D-12 a D-18 y espectros elegidos · 1.5–1.6 D-19 y contrato de `/api/procesar` · 1.7 D-20 y corrección de la sección 4 · 1.8 `enlace_vibracion` y tercer parámetro · 1.9 medición de T-15a · 2.0 umbrales aprobados.)*

---

## 0. Cómo leer este documento

Este plan **no agrega requerimientos**. Todo lo que contiene se deriva de cuatro documentos aprobados, y cuando los cita lo hace por sección:

| Documento | Versión | Qué aporta a este incremento |
|---|---|---|
| Requerimientos y Matriz | V3.2 | RF-04, RF-07, RNF-08, RNF-02; §6.1 parámetros; §6.2 los 7 grupos; §10 criterios CA-05 y CA-08; §11 trazabilidad; §13 riesgo abierto n.º 4 y n.º 6 |
| Diseño detallado de MOD-06 | v2 | §2 enfoque híbrido; §4 tabla de correlación; §5 **contrato de datos (fuente única)**; §6 fusión y umbral; §7 datos y entrenamiento; §8 evaluación; §9 aislamiento; §10 plan B; §11 riesgos |
| Plan de Implementación | V3 | Paso 3 secuencia e interfaces; Paso 4 tareas T-14…T-19; Paso 6 pruebas; Paso 7 hitos y sobrecarga; Paso 8 riesgos |
| Persistencia de datos | v2 | Catálogo JSON y modelo entrenado como archivos de **solo lectura** a través de UT-01; sin base de datos |

**Reglas que siguen vigentes del incremento 1 y 2:**

- Una tarea, un commit. Parar en cada hito (H8, H9, H10) antes de seguir.
- Marcar `SUPUESTO` lo no confirmado, en vez de inventarlo. En este documento los supuestos van señalados en línea.
- Nada «hardcodeado»: los valores salen de UT-03, los mensajes de UT-02, los números de los grupos de UT-01.
- Fronteras explícitas en cada tarea: qué NO se toca.
- Pruebas sin red: ninguna prueba descarga nada; corren offline.
- Pruebas de mutación: romper el código a propósito y confirmar que una prueba revienta.
- Evidencia que se mide, no que se cree.

El Plan V3 autoriza este ajuste: dice que los incrementos 2 a 5 «se revisarán al iniciarlos, ajustando lo que se aprenda del incremento anterior», y que los responsables se asignan al arrancar cada uno.

---

## 1. Decisiones que bloquean el arranque (D-12 … D-18)

Las decisiones D-1 … D-11 ya están cerradas en los planes de los incrementos 1 y 2. Estas siete son nuevas y **ninguna tarea de código debe empezar antes de cerrar las que la bloquean**. Cada una lleva: qué hay que decidir, qué dicen los documentos, las opciones y una recomendación. La recomendación es una propuesta: decide el equipo.

### D-12 · Origen, fase y tamaño del conjunto de entrenamiento — **bloquea T-16a**

**Lo que ya está decidido en los documentos.** Las fuentes son SDBS (AIST) y NIST WebBook (MOD-06 §7). El etiquetado es multi-etiqueta, derivado de la estructura (SMILES) a un vector binario de 7 posiciones. El split es 70 / 15 / 15 sin que un compuesto caiga en dos conjuntos. El riesgo abierto n.º 4 de Requerimientos V3.2 §13 obliga a revisar los términos de uso **antes** de emplear los espectros para ajuste o redistribución, y a reservar un subconjunto independiente para RNF-08.

**Lo que falta decidir.** Cuántos espectros, de qué fase, por qué vía se consiguen y qué se versiona en el repositorio.

**Tres restricciones reales que condicionan la respuesta:**

1. **La descarga de NIST es por especie y manual.** No hay una descarga masiva: se entra a la página del compuesto y se abre «IR Spectrum». Eso ya se comprobó al cerrar T-0R en el incremento 1. SDBS, además, no publica una URL por espectro. `SUPUESTO`: que los términos de uso de SDBS y de NIST permitan usar los espectros para **entrenar** un modelo (no solo para consultarlos) está sin confirmar; es exactamente lo que pide el riesgo n.º 4 y hay que leerlo antes de bajar nada en volumen.
2. **La fase no es un detalle.** En el incremento 1 ya se documentó que la banda ancha e intensa de O–H (GF-01) viene de los puentes de hidrógeno y **prácticamente desaparece en fase gas**. Los dos espectros de referencia que exigen CA-05.1 y CA-05.2 (acetona y ácido benzoico) se bajaron en fase condensada. Entrenar con fase gas y evaluar contra fase condensada rompe el modelo en el grupo más importante del catálogo. **El conjunto debe ser de una sola fase, y esa fase es condensada.** Si un espectro solo existe en fase gas, se etiqueta como tal y se deja fuera del entrenamiento (o se evalúa aparte), nunca mezclado en silencio.
3. **El desbalance de clases es inevitable.** C=O y C–H alifático aparecen en casi cualquier compuesto orgánico; C≡N es raro. Con un conjunto pequeño, los grupos raros quedan con muy pocos ejemplos positivos y su F1 se vuelve inestable (un acierto o un fallo mueven la métrica entera). Esto no se arregla con más épocas: se arregla con más compuestos de esa clase, o se asume y se documenta.

**Opciones:**

| | Opción | Qué cuesta | Qué se obtiene |
|---|---|---|---|
| A | Conjunto curado a mano desde NIST WebBook | Trabajo manual, repartido entre los dos; cada archivo se verifica (fase, rango ≥ 1400–3700, ≥ 300 puntos) y se anota su origen | Datos limpios y de fase conocida, pero pocos; los grupos débiles y raros quedarán cortos |
| B | Buscar un conjunto de espectros IR ya publicado con licencia que permita uso de aprendizaje automático | Tiempo de búsqueda y lectura de licencias, con resultado incierto | Si existe, resuelve el tamaño de golpe. `SUPUESTO`: no está confirmado que exista uno adecuado y con licencia compatible |
| C | Aumentación de datos sobre un núcleo curado (ruido, desplazamiento y pendiente de línea base, pequeños corrimientos, escalado de intensidad) | Poco: es un paso del script de entrenamiento | Mejora la robustez frente a variación instrumental. **No crea diversidad química**: si en el conjunto hay cinco nitrilos, el modelo sigue conociendo cinco nitrilos |

**Recomendación: A + C, y revisar B en paralelo sin que bloquee.** Es la única combinación que arranca esta semana sin depender de que exista algo que no hemos confirmado. Y hay que decirlo con claridad desde ahora: **con un conjunto curado a mano, los grupos débiles (GF-06 C=C y GF-07 anillo aromático) probablemente no lleguen a F1 ≥ 0.80.** Eso no es un fracaso del plan; es lo que el propio diseño de MOD-06 §8 anticipó. Lo que no se puede hacer es descubrirlo al final: por eso D-13 tiene que cerrarse ahora, antes de entrenar.

**Lo que se versiona y lo que no.** El conjunto de espectros **no entra al repositorio**: por licencia (riesgo n.º 4) y por tamaño. Lo que sí entra, y hace la evaluación auditable:

- `datos/dataset/indice.csv` — una fila por espectro: identificador de especie, CAS, fase, rango, nº de puntos, origen, vector de 7 etiquetas y a qué split pertenece.
- `datos/dataset/split-prueba.txt` — la lista **congelada** de identificadores del subconjunto de prueba, con su suma de verificación.
- El script de entrenamiento y su semilla.

Así cualquiera reproduce la evaluación de RNF-08 sin que el repositorio redistribuya datos ajenos.

#### Cerrado el 23/11/2026 — la fase

**El conjunto es de fase condensada; la fase gas queda fuera.** Tres consecuencias que el equipo acepta al tomarla:

- **Se gana coherencia.** Los cinco espectros de referencia (acetona, ácido benzoico, el tercero de T-0R, benzonitrilo y ciclohexeno) son de fase condensada, así que entrenamiento y evaluación miden el mismo régimen. Esto es lo que protege a GF-01.
- **Se pierde volumen.** Una parte importante de los espectros IR públicos de NIST es de fase gas; descartarlos encoge el conjunto disponible, y aprieta justo donde ya duele: en las clases raras.
- **Y aparece una limitación del sistema, no solo del dataset.** Si un usuario sube un espectro de fase gas, el motor trabaja fuera de su régimen: la banda ancha de O–H no existirá y la confianza de GF-01 saldrá baja o nula. La vía de reglas degrada mejor que el modelo, pero tampoco es inmune, porque las posiciones de banda se corren entre fases. **Esto hay que escribirlo** como limitación conocida en §5 de Requerimientos y en el manual de usuario (RNF-07); no basta con dejarlo anotado aquí.

#### Sobre la opción A: sí, es archivo por archivo

Confirmado. El WebBook no tiene descarga masiva: se entra a la página de la especie, se abre «IR Spectrum» y **ahí todavía hay que elegir entre varios espectros del mismo compuesto** —líquido neto, disolución en CCl₄/CS₂, gas, distintas resoluciones— antes de bajar el JCAMP-DX. Más la verificación de rango y de nº de puntos, más la nota de origen. No son segundos por compuesto: son minutos, **con una decisión química en medio**. Por eso el coste de A crece de forma lineal y es el argumento real a favor de B.

#### Sobre la opción C: qué es la aumentación, en concreto

Aumentar es **fabricar variantes creíbles de un espectro que ya tienes, sin cambiar su etiqueta** —la química no cambió—: añadirle algo de ruido, inclinar o desplazar la línea base, correr el espectro uno o dos cm⁻¹, escalar la intensidad. De un espectro real salen, por ejemplo, diez entradas de entrenamiento.

- **Para qué sirve.** Con pocos ejemplos, la red memoriza la curva exacta de esos espectros. Con variantes aprende el *rasgo* —«un pico agudo entre 2210 y 2260»— en vez de «esta curva concreta». Es robustez frente a la variación entre equipos, que es justo lo que RF-03 dice que el sistema debe tolerar.
- **Para qué NO sirve, y es lo importante.** Multiplica copias, no química. Si en el conjunto hay cinco nitrilos, tendrás cinco nitrilos con ruido: el modelo sigue conociendo cinco moléculas. La aumentación arregla fragilidad, no falta de diversidad. Por eso **no sustituye a B**.
- **La regla que la hace honesta.** Se aplica **solo al split de entrenamiento**, nunca a validación ni a prueba. Si una variante de un espectro de prueba se cuela en entrenamiento, el F1 que reporten será mentira y **nadie podrá notarlo desde fuera**.

#### Opción B — RESUELTA el 24/11/2026: **Chemotion IR**

| | |
|---|---|
| **Qué es** | Colección de datos FT-IR del repositorio Chemotion (Karlsruhe Institute of Technology): espectros experimentales de compuestos caracterizados en laboratorios de síntesis, en su mayoría del KIT |
| **Tamaño** | **4 183 archivos `.jdx`** + un `meta_data.json` |
| **Etiquetas** | El metadato trae **`cano_smiles`** por espectro, además de `sample_id`, `kind`, `instrument`, `content` y `authors` |
| **DOI** | `10.22000/OGoEQGlsZGElrgst` |
| **Licencia** | **CC BY-SA 4.0** (atribución + compartir igual) |
| **Cita exigida** | Jung, Nicole; Tremouilhac, Pierre; Punjabi, Dev; Huang, Pei-Chi (2024). *Chemotion repository — data collection: ft-ir spectroscopy data (chemotion ir)*. Karlsruhe Institute of Technology |

**Por qué encaja tan bien, punto por punto:**

- **Son espectros reales, no simulados.** Sin desfase de dominio contra los diez espectros de referencia.
- **Vienen en JCAMP-DX**, que es justo lo que MOD-04 ya sabe leer. T-16b (paridad de preprocesamiento) se vuelve casi trivial: el mismo lector de producción procesa el conjunto de entrenamiento.
- **Traen SMILES canónico**, que es literalmente el método de etiquetado que prescribe MOD-06 §7: derivar el vector binario de 7 posiciones de la estructura.
- **Son datos de caracterización de laboratorio de síntesis**, que en la práctica se miden en fase condensada — coherente con la decisión de fase.

**Referencia publicada, útil como contraste:** Punjabi *et al.*, *Journal of Cheminformatics* 17:24 (2025), acceso abierto CC BY 4.0, entrena una red con NIST SRD 35 más Chemotion y obtiene **F1 por encima de 0.7 para 17 grupos funcionales**. Sirve de vara: la puerta de D-13 (F1 ≥ 0.80 en tres grupos bien marcados, con solo siete clases) es ambiciosa pero no irreal. La mitad NIST de ese trabajo es **SRD 35, que es fase gas** — por eso no se adopta esa parte.

**Cuatro cosas que hay que verificar antes de darlo por bueno (T-16a):**

1. **La fase.** La ficha del conjunto **no describe el método de medición**. Hay que mirar `instrument` y `kind` en el metadato y confirmar que son medidas de fase condensada (ATR o película). Si hubiera una parte en gas, se excluye.
2. **Cuántos sobreviven al pipeline.** Son espectros de laboratorios distintos con instrumentos distintos: habrá archivos que no cubran 1400–3700, que tengan menos de 300 puntos, o con `##YUNITS=` fuera de lo admitido (ya saben lo que eso significa). **Lo primero es pasar los 4 183 por MOD-03 + MOD-04 y contar cuántos pasan.** El propio artículo de Punjabi acaba trabajando con un subconjunto bastante menor que el total, así que esperen merma.
3. **Cuántos positivos por grupo.** Un laboratorio de síntesis orgánica produce mucho C=O, aromático, C–H, O–H y N–H; **GF-04 (C≡N) y GF-06 (C=C) pueden seguir escasos** aun con 4 183 espectros. El conteo de support por clase de T-16a decide si el desbalance sigue siendo el problema.
4. **La licencia, que es lo que más cuidado pide.** CC BY-SA 4.0 obliga a **atribuir** y a **compartir igual** las obras derivadas. No soy abogado y esto conviene que lo mire alguien del equipo o un profesor, pero lo prudente y además coherente con lo ya decidido es: **no redistribuir los espectros en el repositorio** (ya estaba decidido), **citar el conjunto** en el README y en el reporte de RNF-08, y **dejar anotada la licencia de origen** junto al archivo de pesos si se versiona. El riesgo real en un proyecto académico es bajo; el descuido de no citar, no.

> **Y queda una lección registrada:** este conjunto existía desde 2024 y la búsqueda inicial del equipo no lo encontró porque se buscaba «dataset de espectros IR». Apareció al buscar por el **problema** —identificación de grupos funcionales con redes neuronales— y llegar al conjunto a través del artículo que lo usa. Para la siguiente búsqueda de datos, ese es el camino: buscar quién resolvió el problema y mirar con qué datos lo hizo.

#### Cerrado el 23/11/2026 — el origen: A + B, con C como técnica de entrenamiento

- **A** — núcleo curado a mano desde NIST WebBook (lista de abajo). **Se reserva para prueba y validación.**
- **B** — conjunto publicado con licencia compatible. **Encontrado el 24/11/2026: Chemotion IR, 4 183 espectros reales con SMILES. Ver abajo.** Es el conjunto de **entrenamiento**.
- **C** — aumentación, aplicada **solo al split de entrenamiento**. Con B resuelto pasa de ser necesaria a ser opcional: se usa si el support de GF-04 o GF-06 sigue bajo.

#### Para qué se usa el núcleo curado (y para qué no)

Conviene decirlo antes de que nadie baje un archivo, porque cambia la estrategia entera: **un conjunto curado a mano de ~20 compuestos no sirve para entrenar un CNN, ni aumentado.** La aumentación multiplicaría veinte moléculas, no crearía la vigésimo primera. Pero **sí es exactamente lo que hace falta** para lo otro:

- el **subconjunto de prueba independiente de RNF-08**, que tiene que ser limpio, de fase conocida y verificado a mano — un conjunto masivo bajado en bloque nunca tendrá esa calidad;
- las **fixtures de la vía de reglas** (T-15), que necesitan cubrir los 7 grupos;
- el **split de validación** con el que se recalibran los pesos (D-15).

Por eso: **el núcleo curado se reserva para prueba y validación; el grueso del entrenamiento depende de B.** Si B no aparece, se entrena con lo que haya y lo más probable es que se active el plan B de D-16 — pero el núcleo curado habrá hecho su trabajo igual, porque la vía de reglas se apoya en él.

> **Regla anti-contaminación para cuando llegue B:** antes de entrenar, **quitar del conjunto de entrenamiento todo compuesto que esté en `split-prueba.txt`**, comparando por InChIKey o CAS, **nunca por nombre** (el mismo compuesto aparece como «styrene», «vinylbenzene» y «ethenylbenzene»). Si un compuesto del dataset grande coincide con uno del núcleo curado, manda el núcleo: se queda en prueba y sale de entrenamiento.

#### Qué más descargar (A) — la lista

Lo que falta no son *más copias*, sino **más moléculas distintas por grupo**, y sobre todo moléculas que **rompan correlaciones falsas**. Si todos sus nitrilos son aromáticos, el motor aprenderá que un nitrilo implica un anillo. Cada fila de abajo está elegida por lo que aporta, no por rellenar.

**Cobertura actual, confirmada el 23/11/2026** (el tercer archivo de T-0R resultó ser `62-53-3` = **anilina**, así que GF-02 ya estaba cubierto):

| Grupo | Lo cubren hoy | Estado |
|---|---|---|
| GF-01 O–H | ácido benzoico | Solo el **O–H de ácido** (2500–3300). **Falta el O–H de alcohol/fenol** (3200–3550), que es el caso del catálogo |
| GF-02 N–H | anilina | Solo amina **aromática** |
| GF-03 C–H alif. | acetona, ciclohexeno | Siempre acompañado de otro grupo; **no hay ningún negativo limpio** |
| GF-04 C≡N | benzonitrilo | Solo nitrilo **aromático** |
| GF-05 C=O | acetona (cetona), ácido benzoico (ácido) | Faltan **éster** y **aldehído** |
| GF-06 C=C | ciclohexeno | Uno solo |
| GF-07 aromático | ácido benzoico, anilina, benzonitrilo | Tres, pero **ninguno es un aromático limpio** |

Los siete grupos tienen al menos un espectro, así que **la vía de reglas (T-15) ya no está bloqueada**. Lo que falta son las moléculas que rompen correlaciones falsas y llenan los huecos de la columna «Estado»:

| Prioridad | Buscar | Grupos que aporta | Por qué ese |
|---|---|---|---|
| **1** | `acetonitrile` | GF-04 + GF-03 | **Rompe** la correlación nitrilo ↔ aromático que crearía el benzonitrilo solo |
| **1** | `toluene` | GF-07 + GF-03 | Aromático limpio, sin O–H, sin C=O. El aromático «de libro» |
| **1** | `1-hexene` | GF-06 + GF-03 | Alqueno terminal: segundo C=C, con =C–H claro |
| **1** | `phenol` | GF-01 + GF-07 | O–H **sin** C–H alifático: rompe la correlación O–H ↔ alifático |
| **1** | `ethyl acetate` | GF-05 (éster) + GF-03 | C=O de éster ~1740: si todos sus C=O son cetonas, el motor no verá un éster |
| **1** | `hexane` o `cyclohexane` | GF-03 solo | **Negativo limpio de todo lo demás.** Sin negativos, el motor no aprende a decir que no |
| 2 | `acetic acid` | GF-01 (ácido) + GF-05 | O–H ancho de ácido sin anillo: rompe la correlación ácido ↔ aromático del ácido benzoico |
| 2 | `benzaldehyde` | GF-05 (aldehído) + GF-07 | Tercer subtipo de C=O |
| 2 | `butylamine` o `propylamine` | GF-02 + GF-03 | N–H alifática, sin anillo |
| 2 | `2-butanone` o `cyclohexanone` | GF-05 (cetona) | Cetona distinta de la acetona |
| 2 | `acetamide` o `N-methylacetamide` | GF-02 + GF-05 (amida) | El C=O de amida baja a 1630–1700, el extremo del rango |
| 3 | `propanenitrile` | GF-04 | Tercer nitrilo: GF-04 es el que menos ejemplos tendrá |
| 3 | `1-butanol` | GF-01 + GF-03 | Alcohol alifático (el etanol se descartó en T-0R por no tener opción condensada limpia) |
| 3 | `chlorobenzene` u `o-xylene` | GF-07 | Cuarto aromático |
| 3 | `1-octene` | GF-06 | Cuarto alqueno: GF-06 es el otro grupo escaso |

**Si el tiempo aprieta, bajen solo la prioridad 1**: son **seis** archivos (la anilina ya la tienen) y con ellos cada grupo queda cubierto por al menos dos moléculas distintas, y las cuatro correlaciones falsas peligrosas quedan rotas.

#### Enlaces directos a la página de IR, en orden de descarga

El patrón de URL de la página de espectro IR del WebBook es `cgi/inchi?ID=<ID>&Mask=80` (verificado). En cada una: elegir la entrada, abrirla y usar **«Download spectrum in JCAMP-DX format»**.

| # | Compuesto | ID | Enlace |
|---|---|---|---|
| 1 | Tolueno | `C108883` | https://webbook.nist.gov/cgi/inchi?ID=C108883&Mask=80 |
| 2 | Ciclohexano | `C110827` | https://webbook.nist.gov/cgi/inchi?ID=C110827&Mask=80 |
| 3 | Fenol | `C108952` | https://webbook.nist.gov/cgi/inchi?ID=C108952&Mask=80 |
| 4 | Acetonitrilo | `C75058` | https://webbook.nist.gov/cgi/inchi?ID=C75058&Mask=80 |
| 5 | 1-Hexeno | `C592416` | https://webbook.nist.gov/cgi/inchi?ID=C592416&Mask=80 |
| 6 | Acetato de etilo | `C141786` | https://webbook.nist.gov/cgi/inchi?ID=C141786&Mask=80 |

#### Resultado de la revisión de entradas (23/11/2026)

Al abrir las páginas apareció un patrón que conviene dejar escrito: **en la colección Coblentz, la entrada de líquido neto es la minoría**; para muchos compuestos lo único condensado es una disolución en CCl₄/CS₂.

| # | Compuesto | Entrada elegida | Estado |
|---|---|---|---|
| 1 | **Tolueno** `C108883` | `LIQUID; PERKIN-ELMER; DIGITIZED BY NIST FROM HARD COPY; 4 cm⁻¹` (Coblentz) | ✅ Neto, sin disolvente |
| 2 | **Ciclohexano** `C110827` | `LIQUID (NEAT); DOW KBr FOREPRISM-GRATING; DIGITIZED BY COBLENTZ SOCIETY (BATCH I); 2 cm⁻¹` | ✅ Neto, 2 cm⁻¹. **Ojo: es compuesto distinto del ciclohexeno `110-83-8`** |
| 3 | **Fenol** `C108952` | **descartado** → ciclohexanol tampoco tenía neto → **1-butanol `C71363`**: `LIQUID (NEAT); PERKIN-ELMER 521 (GRATING); 4 cm⁻¹` | ✅ Resuelto. Ver abajo |
| 4 | **Acetonitrilo** `C75058` | `LIQUID (NEAT); BECKMAN IR-9 (GRATING); 4 cm⁻¹` (Coblentz) | ✅ Neto |
| 5 | **1-Hexeno** `C592416` | sin entrada neta → `1-octene` como sustituto | ⚠️ Ver abajo |
| 6 | **Acetato de etilo** `C141786` | sin entrada neta → `butyl acetate` `C123864` o `methyl acetate` | ⚠️ Ver abajo |

**Fenol: se descarta, y por una razón química, no por el disolvente.** Sus únicas entradas son gas y una disolución al 10 % en CCl₄/CS₂. En disolución diluida el O–H del fenol queda en buena parte **sin asociar**, y aparece como una banda **angosta de O–H libre cerca de 3600 cm⁻¹** en lugar de la banda ancha por puentes de hidrógeno que el catálogo describe para GF-01 en 3200–3550. Es el mismo motivo por el que en T-0R se descartó el etanol. Como fixture de GF-01 **enseñaría lo contrario de lo que queremos**. Sustituto confirmado: **ciclohexanol `C108930`** (verificado: tiene IR de Coblentz), que además es alcohol **no aromático** y así rompe la correlación O–H ↔ anillo que hoy crea el ácido benzoico. Enlace: `https://webbook.nist.gov/cgi/inchi?ID=C108930&Mask=80`

> **Resuelto el 23/11/2026:** el ciclohexanol **no tenía entrada neta** (funde cerca de la temperatura ambiente), así que GF-01 lo cubre **1-butanol `C71363`** con su `LIQUID (NEAT); PERKIN-ELMER 521 (GRATING); 4 cm⁻¹`. Mejor incluso: es líquido sin ambigüedad y alcohol alifático, así que aporta O–H ancho **y** C–H alifático sin anillo. Sus otras dos entradas eran disoluciones al 0.5 % y al 10 % en CCl₄/CS₂ — la del 0.5 % habría sido la peor opción posible para GF-01, porque a esa dilución el O–H queda prácticamente sin asociar y la banda ancha desaparece.

**1-Hexeno y acetato de etilo: sin entrada neta.** Solo gas o disolución en CCl₄/CS₂. El riesgo concreto es el de siempre: el artefacto de CCl₄ en ~1550 cm⁻¹ cae en 1450–1600 (**GF-07**), y **ninguno de los dos tiene anillo aromático**, así que produciría un falso positivo justo del tipo que R-2 debe suprimir. Orden de acción: (1) probar el sustituto con entrada neta — `1-octene` para GF-06, `butyl acetate` o `methyl acetate` para el éster; (2) si tampoco hay, descargar la disolución, **leer su cabecera** y aceptarla solo si no declara contaminación en 1450–1600, dejándolo anotado en la nota de origen.

> **Y si la disolución resulta contaminada, no se tira: se convierte en prueba.** Un espectro real de un compuesto **sin** anillo aromático que lleva un artefacto en la región aromática es el caso perfecto para verificar R-2 con datos reales en vez de sintéticos. Se guarda en `datos/referencia/` etiquetado, igual que se hizo con el estireno.

**Urgencia relativa:** el que de verdad falta es el **ciclohexano** (único negativo limpio) junto con tolueno y acetonitrilo, que ya están resueltos. El alqueno y el éster son refuerzos: GF-06 ya tiene al ciclohexeno y GF-05 ya tiene cetona y ácido.

#### Cómo reconocer de qué colección viene cada entrada

Esto importa porque es lo que falló con el estireno. El WebBook mezcla varias colecciones de IR y **se distinguen por la línea «Data compiled by»**:

- **Coblentz Society, Inc.** — las de acetona, ácido benzoico, anilina, benzonitrilo y ciclohexeno. Fase condensada o disolución, en transmitancia. Son las que mejor encajan con §6.1.
- **NIST Mass Spectrometry Data Center (William E. Wallace)** — las de fase gas. Fuera por la decisión de fase.
- **IARPA / PNNL Liquid Phase IR Spectra** (Myers, Tonkyn, Oeck, Danby, Loring, Taubman, Sharpe, Birnbaum, Johnson) — líquidos de altísima resolución. **De aquí salió el estireno con `dispersion index`.** No se descartan de entrada: esta colección publica varias magnitudes derivadas y algunas sí son absorbancia. **Simplemente hay que abrir el `.jdx` y mirar `##YUNITS=` antes de aceptarlo.**

**Regla, para los seis y para cualquiera que venga después:** entrada de líquido neto · sin CCl₄/CS₂ · sin gas · **`##YUNITS=` en transmitancia o absorbancia** · rango que cubra 1400–3700 · ≥ 300 puntos · nota de origen.

**Mismo criterio de elección en todos:** entrada de **líquido neto** (`LIQUID (NEAT)` o equivalente), **nunca** una disolución en CCl₄/CS₂, **nunca** gas. Si un compuesto no ofrece líquido neto, se cambia por otro de la misma fila en vez de bajar una disolución. Y cada archivo con su nota de origen: ID, fase, rango, puntos, grupos que cubre, fecha.

---

### D-13 · Qué significa exactamente «alcanzar RNF-08» — **bloquea el criterio de terminado de T-16**

Esta es la decisión más importante del incremento, y existe porque **dos documentos aprobados dicen cosas distintas**:

- **Requerimientos V3.2, RNF-08:** «el motor debe alcanzar una puntuación F1 promedio ≥ 0.80 **en los siete grupos** (meta inicial, **a confirmar en la fase de diseño**)».
- **Diseño de MOD-06 v2, §8:** «Meta: F1 ≥ 0.80 **en los grupos bien marcados** (C=O, O–H, C≡N). Los débiles (C=C, anillo aromático) serán más bajos — **documentarlo, no ocultarlo**».

No es una contradicción de fondo: RNF-08 delega su confirmación a la fase de diseño, y la fase de diseño la refinó. El Plan V3 ya está alineado con el diseño (el «Terminado» de T-16 dice «meta F1 ≥ 0.80 en los grupos bien marcados»). **Lo único que falta es cerrarlo por escrito**, para que «terminado» signifique lo mismo para quien entrena y para quien revisa.

**Propuesta de cierre — el criterio de aceptación de T-16 es el conjunto de estos cuatro puntos:**

1. **Puerta (lo que decide pasa/no pasa):** F1 ≥ 0.80 **por grupo** en GF-01 (O–H), GF-04 (C≡N) y GF-05 (C=O), medido sobre el subconjunto de prueba independiente.
2. **Informativo (se reporta siempre, nunca se oculta):** precisión, recall, F1 y nº de positivos (*support*) de **los siete** grupos, más el macro-F1 global y la matriz de confusión uno-contra-resto. Si el macro-F1 de los siete queda por debajo de 0.80, se escribe el número y se explica por qué, con el support de cada clase a la vista.
3. **Dos evaluaciones, no una.** MOD-06 §8 y el Plan V3 piden cosas distintas en sitios distintos, y ambas se hacen: (a) **la vía ML sola**, binarizando su sigmoide en 0.5, que es lo que mide si el modelo aprendió; (b) **el motor completo**, post-fusión y con el umbral de 60 %, que es lo que el usuario recibe. Las dos tablas van en la evidencia.
4. **Si falla un grupo de la puerta** (típicamente GF-04 por falta de ejemplos), no se baja la meta: se activa la ruta de D-16.

**Por qué importa tanto:** sin esto, T-16 no tiene criterio de terminado y se cierra «cuando parezca suficiente». Con esto, el plan B deja de ser una excusa de última hora y se vuelve una decisión con disparador definido.

#### Cerrado el 23/11/2026: se adopta la propuesta tal cual

**Dónde se actualiza la decisión del F1**, en cuatro sitios y por este orden:

| Documento | Sección exacta | Qué cambia |
|---|---|---|
| **Requerimientos y Matriz V3.2** | **§8, fila RNF-08** | Es el origen de la ambigüedad. Hoy dice «F1 promedio ≥ 0.80 en los siete grupos (meta inicial, **a confirmar en la fase de diseño**)». Esa cláusula ya se cumplió: se reescribe con la **puerta** (F1 ≥ 0.80 por grupo en GF-01, GF-04 y GF-05) y la obligación de **reportar los siete** con su support |
| **Requerimientos y Matriz V3.2** | **§11.2, fila RNF-08** | Hoy dice «F1 por grupo y promedio ≥ 0.80». Se alinea palabra por palabra con el texto nuevo de §8 |
| **Requerimientos y Matriz V3.2** | **Control de versiones** (p. 3) | Fila nueva **V3.3** con la descripción del cambio y su fecha. Aprovechar la misma versión para el pendiente del `.dx` en RF-01 |
| **Diseño detallado de MOD-06 v2** | **§8, «Evaluación y pruebas»** | Ya dice lo correcto en espíritu; se le añade la redacción literal de la puerta para que ambos documentos digan lo mismo. Versión v2.1 |

El **Plan de Implementación V3 no necesita cambio**: el «Terminado» de T-16 (Paso 4) y la fila de riesgo del Paso 8 ya están alineados con esta lectura.

Y una regla de higiene, la misma que usaron con los 5 MB para evitar la deriva: **el criterio operativo vive aquí (D-13); Requerimientos solo enuncia la regla.** Nadie copia el número a un tercer sitio.

---

### D-14 · Los dos espectros que faltan: GF-04 (C≡N) y GF-06 (C=C) — **bloquea T-3R y los CA de regla**

De los tres espectros reales que se bajaron en T-0R (acetona, ácido benzoico y un tercero), **ningún compuesto cubre C≡N ni C=C**. Quedó anotado en el incremento 1 como herencia explícita para el incremento 3. Sin ellos, la vía de reglas no se puede probar en dos de los siete grupos y el dataset arranca con dos clases vacías.

**Propuesta, con los identificadores verificados en el WebBook:**

| Grupo | Compuesto | CAS | ID de especie NIST | Por qué este |
|---|---|---|---|---|
| **GF-04 (C≡N)** | Benzonitrilo | 100-47-0 | `C100470` | Verificado: su página lista «IR Spectrum». Ventaja doble — además del C≡N trae **anillo aromático y C–H aromático**, así que sirve también como caso multi-etiqueta (GF-04 + GF-07) |
| **GF-06 (C=C)** | Ciclohexeno | 110-83-8 | `C110838` | Verificado: su página lista «IR Spectrum». Ventaja clave — **no tiene anillo aromático**, así que aísla GF-06 de GF-07 y permite probar la regla de desempate desde el lado limpio |
| **Caso difícil (GF-06 + GF-07)** | Estireno | 100-42-5 | `C100425` | Verificado: su página lista «IR Spectrum». Vinilo C=C ~1630 **y** anillo aromático 1600/1500, con =C–H y C–H aromático ambos por encima de 3000. Si la regla R-2 sobrevive al estireno, sobrevive a cualquier cosa |

**Advertencia honesta sobre el ciclohexeno:** su C=C es una banda **débil** y su =C–H cerca de 3020 cm⁻¹ también. No es un espectro fácil — es un espectro *representativo*. Si la vía de reglas detecta GF-06 aquí, detecta GF-06 de verdad; si se eligiera un alqueno con una señal artificialmente clara, la prueba pasaría sin decir nada útil.

**Disciplina que se hereda de T-0R y se mantiene:** `SUPUESTO` — la página de especie de NIST **no declara la fase** del espectro IR; hay que verla al abrir el espectro. Cada archivo nuevo se guarda con su nota de origen: ID de especie, CAS, **fase**, rango cubierto, nº de puntos, qué CA o qué grupo cubre y fecha de descarga. Y se revisan los términos de uso antes de versionarlo (las páginas de NIST llevan la nota de *data compilation copyright* del U.S. Secretary of Commerce).

#### Cerrado el 23/11/2026: cuál descargar de cada uno

Cada compuesto ofrece **varios** espectros IR, y la elección no es indiferente. Estos son los tres:

| Grupo | Compuesto | Entrada exacta a descargar | Por qué esa y no las otras |
|---|---|---|---|
| **GF-04** | Benzonitrilo `C100470` | **LIQUID; PERKIN-ELMER; DIGITIZED BY NIST FROM HARD COPY; 4 cm⁻¹** | Es el único de fase condensada **sin disolvente**. Las otras tres son disoluciones «versus solvent» en CCl₄ y CS₂ — exactamente la familia de archivo que dejó la contaminación de CCl₄ en ~1550 cm⁻¹ en la acetona (R-3). Bajar una de esas sería meter un falso GF-07 **en un compuesto que sí tiene anillo aromático**, y entonces ya no se podría distinguir señal de artefacto. El `gas; HP-GC/MS/IRD` queda fuera por la decisión de fase |
| **GF-06** | Ciclohexeno `C110838` | **LIQUID (NEAT) $$ 99.9% PURE; BECKMAN IR-12 (GRATING); 2 cm⁻¹** | Neto, fase condensada y **con pureza declarada**, que aquí importa de verdad: el ciclohexeno comercial suele venderse estabilizado con un inhibidor fenólico, y un fenol mete un O–H que daría un **GF-01 falso en un hidrocarburo**. El 99.9 % minimiza ese riesgo. Segunda opción: el `LIQUID (NEAT)` sin nota de pureza. Fuera: los dos de gas y el `LIQUID (60 mmHg diluido … con nitrógeno)`, cuya descripción es de condiciones de gas |
| **GF-06 + GF-07** | **descartado el estireno** — ver abajo | — | El caso «ambos a la vez» baja a prioridad 2 y se cubre de otra forma |

#### El estireno quedó descartado como referencia (23/11/2026)

Se descargó y su cabecera trae **`##YUNITS=dispersion index`**. Eso **no sirve**: §6.1 admite únicamente transmitancia o absorbancia, y esta magnitud pertenece a la familia de las constantes ópticas (índice de refracción / dispersión), no a una medida de absorción. Las otras entradas del estireno tampoco valen: dos son de gas y dos son disoluciones en CCl₄/CS₂, con el artefacto justo entre las bandas aromáticas de 1600 y 1500.

**Y el archivo es más útil de lo que parece: se guarda como caso de error real.** Hoy MOD-03 valida estructura, puntos y rango, pero **no la unidad**, así que este archivo **pasaría la validación**, llegaría a MOD-04 y el motor analizaría números que no son intensidades — con gráfica y detecciones sin ningún significado químico. Es el ejemplo concreto que le faltaba a la decisión abierta sobre `##YUNITS=` (sección 12), y se versiona en `datos/referencia/` marcado como caso de error, igual que se hizo en el incremento 1 con los otros dos de unidad rara.

**Cómo se cubre entonces el desempate C=C / aromático (R-2), que era el objetivo:**

1. **Con un par de espectros, no con un compuesto** — y de hecho es la prueba más fuerte, porque discrimina en las dos direcciones:
   - **ciclohexeno** → GF-06 **sí**, GF-07 **no**
   - **tolueno** → GF-07 **sí**, GF-06 **no**

   Los dos están ya en la lista de descargas, así que esto no cuesta nada extra y cierra R-2.
2. **El caso «ambos a la vez»** —que solo prueba que se puedan reportar juntos, una propiedad más suave— pasa a **prioridad 2**. Candidatos a revisar en el WebBook, buscando entrada de líquido neto y unidad admitida: `indene`, `allylbenzene`, `alpha-methylstyrene`. Si ninguno tiene una entrada utilizable, se deja documentado y se vive con ello: el par del punto 1 ya protege la regla.

**Al descargar cada uno, verificar antes de guardarlo** (la misma lista de T-0R): que cubra **1400–3700 cm⁻¹**, que tenga **≥ 300 puntos**, y anotar fase, rango, nº de puntos, ID de especie, qué grupo cubre y la fecha. Si un archivo no cumple rango o puntos, se elige otra entrada del mismo compuesto antes de cambiar de compuesto.

---

### D-15 · Umbral, pesos y la aritmética del 60 % en UT-03 — **bloquea T-17**

**Lo decidido en los documentos:** umbral 60 % (0.6), configurable en UT-03 (Requerimientos §6.1, MOD-06 §6). Pesos `conf = wR·score_regla + wML·prob_ml`, con `wR + wML = 1`, arrancando en 0.5 / 0.5 y ajustando con validación.

**Lo que falta cerrar, en cuatro puntos:**

**1. Las claves en `parametros.json` y su invariante.** Propuesta: `umbral_confianza: 0.6` y `pesos: { wR: 0.5, wML: 0.5 }`. UT-03 ya valida la configuración al cargar (criterio de terminado de T-01); se le añade la verificación de que `wR + wML = 1` y de que ambos están en [0, 1]. Si no cuadra, el backend no arranca en silencio: error de configuración claro, igual que en el incremento 1.

**2. La recalibración usa el split de validación, nunca el de prueba.** Esto es lo que hace honesto a RNF-08. El subconjunto de prueba se toca **una sola vez**, al final, para reportar. Si se ajustan los pesos mirando la prueba, el número que se entrega deja de significar nada y nadie fuera del equipo podrá notarlo. Regla dura, sin excepciones.

**3. La banda «posible» (0.4–0.6) queda FUERA del incremento 3.** MOD-06 §6 la marca como opcional; ningún CA la cubre; y mostrarla cambiaría lo que MOD-01 pinta y lo que el reporte del incremento 5 tendría que explicar. Propuesta: no implementarla. Si el equipo la quiere, es una decisión de alcance con su propio CA, no un añadido silencioso.

**4. La trampa aritmética del 60 % — y es una trampa real.** CA-05.3 exige que **exactamente 60 % aparezca** y **59 % no**; CA-08.2 exige que un máximo de 59 % dispare el aviso. Pero `conf` es un número de punto flotante y la interfaz muestra un porcentaje redondeado. Si se compara el flotante crudo contra 0.6 y se redondea aparte para mostrar, un 0.599 se muestra como «60 %» y **no** aparece detectado: la pantalla contradice al veredicto, y el usuario ve un 60 % que el sistema dice que no alcanza el 60 %.

> **Propuesta:** calcular primero el porcentaje entero (redondeo al más cercano) y **comparar ese entero contra 60**. Veredicto y pantalla salen del mismo número, así que no pueden contradecirse, y CA-05.3 / CA-08.2 se cumplen literalmente.
>
> **El precio, dicho de frente:** un `conf` de 0.5951 se convierte en 60 % y se reporta como detectado, aunque crudo no llegue a 0.6. Es medio punto porcentual de holgura a cambio de que nunca haya una pantalla que se contradiga. La alternativa —comparar el flotante y truncar hacia abajo para mostrar— elimina la holgura pero obliga a definir el redondeo con el mismo cuidado. Cualquiera de las dos sirve **si queda escrita**; lo que no sirve es dejarlo al criterio de quien implemente.

**Cerrado el 23/11/2026:** se adoptan los cuatro puntos. El umbral se compara sobre el **porcentaje entero redondeado**, con la holgura de medio punto aceptada a cambio de que pantalla y veredicto no puedan contradecirse.

---

### D-16 · El plan B (`wML = 0`): disparador y forma del contrato — **bloquea T-17 y T-19**

**Lo decidido:** si el CNN no alcanza las métricas a tiempo, se entrega con `wML = 0` (solo reglas) sin cambiar el contrato ni el resto de la app (MOD-06 §10, Plan V3 Paso 8). La vía de reglas ya identifica de punta a punta por sí sola — es la Fase 1 del diseño.

> **La decisión es una sola: ¿cuándo nos rendimos con el modelo y entregamos solo con reglas, y quién lo dice?** Eso es el punto 1. Los puntos 2, 3 y 4 **no son decisiones del equipo**: son instrucciones para el agente de código, para que ese cambio no rompa nada el día que ocurra. Basta con aprobarlos.

**Lo que falta cerrar:**

**1. El disparador — ESTA es la decisión.** Propuesta: se evalúa **al cerrar H9**, y se activa el plan B si ocurre cualquiera de estas tres cosas:
- la vía ML no cumple la puerta de D-13;
- el conjunto de datos (T-16a) no está cerrado cuando T-15 termina;
- la inferencia del modelo no cabe en el presupuesto de RNF-02 (≤ 5 s por análisis, CPU).

`SUPUESTO`: la fecha límite de calendario. Los documentos no fijan fechas y este plan no las inventa. El disparador está amarrado a un **hito**, no a un día; el equipo le pone la fecha al asignar responsables.

**2. Quién decide.** El equipo, por escrito en este documento y en la bitácora de IA. No lo decide quien está entrenando, y no se decide a mitad de una tarea.

**3. La forma del contrato — aquí está el detalle que ahorra una ruptura más adelante.** Con `wML = 0`, `conf = score_regla` y la vía ML no produce nada. Pero el JSON de MOD-06 §5 publica `"evidencia": { "regla": 0.97, "ml": 0.91 }`, y MOD-07 (incremento 4) y MOD-08 (incremento 5) lo van a leer.

> **Propuesta:** `evidencia.ml` **se mantiene como clave** y vale `null` cuando no hay vía ML. Y se añade un campo `"modo": "hibrido" | "reglas"` al resultado.
>
> Dos razones. Una: quitar la clave rompería a los consumidores, mientras que agregar un campo opcional no rompe a nadie. Dos: **MOD-07 y MOD-08 deben tratar `ml` como anulable desde el primer día**, aunque hoy el modo híbrido funcione. Hacerlo ahora cuesta cero; descubrirlo en el incremento 5, cuando el PDF reviente al generarse en modo reglas, cuesta una tarde.
>
> Y hay una consecuencia honesta: si el motor corrió en modo reglas, el reporte del incremento 5 debería decirlo, junto al aviso de resultado orientativo que ya exige RF-08. Queda anotado como herencia, no se implementa aquí.

**4. El modelo ausente en tiempo de ejecución.** Si el archivo de pesos no está, la app **arranca en modo reglas** y lo registra; no revienta ni se queda esperando. Esto es distinto de CA-05.4 (fallo interno del motor): ahí sí hay mensaje de error al usuario. Falta de modelo = degradación anunciada; fallo del motor = error. Dos códigos distintos en UT-02.

**Cerrado el 23/11/2026:** se adoptan los cuatro puntos. El plan B se evalúa **al cerrar H9** y se activa si falla la puerta de D-13, si el conjunto de datos no está listo cuando T-15 termina, o si la inferencia no cabe en los 5 s de RNF-02. **Lo decide el equipo junto y por escrito** — no quien esté entrenando, y no a mitad de una tarea.

---

### D-17 · El contrato HTTP de «Analizar» — **bloquea T-18**

`SUPUESTO`, y lo primero que hay que resolver **leyendo el código del incremento 2**, no de memoria: no está confirmado en los documentos qué endpoints existen hoy. El incremento 1 montó `POST /api/validar` (contrato D-5). Si el incremento 2 añadió algo para entregar el espectro procesado al navegador, este contrato se acopla a eso.

El problema de fondo: la app es **sin estado** y no persiste nada (RNF-09). Cuando el usuario pulsa «Analizar» (paso 2 de los tres de RNF-01), el servidor ya no tiene el espectro. Hay dos salidas:

| | Opción | A favor | En contra |
|---|---|---|---|
| 1 | `POST /api/analizar` recibe **el vector normalizado y el eje** (JSON) y devuelve la salida de MOD-06 §5 | Sin estado y barato (el navegador ya tiene el vector: MOD-05 lo está graficando). Y encaja exactamente con el aislamiento del diseño: «MOD-06 solo recibe números, **nunca el archivo**» | El cliente podría mandar un vector arbitrario → hay que validar lo que llega |
| 2 | Se reenvía el archivo y el servidor vuelve a correr MOD-03 → MOD-04 → MOD-06 | Un solo contrato, ya conocido | Reparsea de gratis, mete el archivo otra vez en la ruta de análisis y gasta presupuesto de RNF-02 |

**Recomendación: opción 1**, porque es la que el propio diseño describe. Con una condición no negociable: **el endpoint valida lo que llega** antes de pasárselo al motor —longitud igual a la rejilla fija, valores dentro de [0, 1], eje monótono de 4000 a 400— y rechaza con su código de UT-02. No hay cuentas ni datos de terceros en juego, pero un vector mal formado no debe llegar al modelo.

#### Cerrado el 23/11/2026: opción 1, y con dato nuevo del incremento 2

Ya existe **`POST /api/procesar`**, añadida para entregarle el espectro a la gráfica en lugar de cambiar la respuesta de `/api/validar`, que el incremento 1 dejó cerrada (quedó anotada al final de `docs/plan/incremento-2.md`, junto con los supuestos). **Esa decisión es correcta y queda confirmada por el equipo:** no tocar un contrato cerrado y añadir una ruta nueva es exactamente la disciplina de fronteras del proyecto.

El incremento 3 **añade `POST /api/analizar`** junto a las otras dos; no modifica ninguna. El navegador ya tiene el vector normalizado —viene de `/api/procesar` y lo está graficando MOD-05—, así que lo reenvía tal cual. Las tres rutas quedan alineadas con los tres pasos de RNF-01:

```
/api/validar (inc. 1)  →  /api/procesar (inc. 2)  →  /api/analizar (inc. 3)
   cargar                      ver la gráfica            analizar
```

Sigue en pie la condición: `/api/analizar` **valida lo que llega** (longitud igual a la rejilla fija, valores en [0, 1], eje monótono de 4000 a 400) y rechaza con su código de UT-02 antes de tocar el motor.

**El contrato de `/api/procesar`, confirmado por el incremento 2** (§11 de `incremento-2.md`). Recibe `multipart/form-data` con el archivo en el campo `archivo` y responde 200 con:

```
{ "valido": true, "nombre": "...",
  "espectro": { "eje_cm1": [...], "intensidad": [...],
                "rango_medido_cm1": [min, max], "unidad_original": "..." } }
```

**`/api/analizar` recibe en JSON exactamente ese objeto `espectro`** — tal como lo propuso quien implementó el incremento 2. No se inventa un formato nuevo y el navegador reenvía lo que ya tiene.

**Códigos de error: se reutilizan los que ya existen, no se duplican.** MOD-04 ya definió `DATOS_ILEGIBLES`, `UNIDAD_NO_SOPORTADA`, `UNIDAD_SIN_DECLARAR` y `SIN_SENAL`, y un fallo interno responde **500 con `FALLO_INTERNO`**. **CA-05.4 (fallo del motor) usa `FALLO_INTERNO`**, que ya está hecho y probado; MOD-06 solo añade lo suyo (vector inválido, y el registro interno de modelo ausente).

El tamaño N se cierra en **D-19**.

---

### D-18 · Dónde vive el modelo entrenado y si se versiona — **bloquea T-16c**

> **La decisión es una sola: el archivo del modelo entrenado, ¿lo subimos a GitHub o no?** Es una pregunta y no un trámite porque es un **binario que cambia entero en cada reentrenamiento**, y Git guarda todas las versiones para siempre: a los veinte entrenamientos el repositorio pesa veinte modelos aunque solo se use el último, y eso lo arrastra cualquiera que clone. Lo demás de esta sección no es decisión: es una aclaración para el agente de código.

La decisión de persistencia v2 ya dice qué es: un **archivo de pesos de solo lectura** en `motor_identificacion/modelo/`, leído a través de UT-01, igual que el catálogo. Lo que falta es si entra a Git.

- **Durante la iteración:** fuera de Git (`.gitignore`). Un binario que cambia en cada entrenamiento infla el historial sin aportar nada.
- **Para la entrega:** se versiona **un** archivo de pesos final, junto con el script de entrenamiento, la semilla y `split-prueba.txt`. Así la evaluación de RNF-08 es reproducible sin redistribuir el dataset.
- Si el archivo final resulta demasiado grande para el repositorio, la alternativa es Git LFS; decidirlo cuando se sepa el tamaño real, no antes.

**Un detalle de aislamiento que conviene dejar escrito**, porque el diseño parece contradecirse y no lo hace: MOD-06 §9 dice «sin acceso a red ni a archivos», y también «el modelo se carga una vez en memoria». Se resuelve así: **la carga ocurre al arrancar, a través de UT-01**, que es el único módulo que toca el sistema de archivos (persistencia v2). En tiempo de inferencia MOD-06 no toca disco ni red. Sin esta frase, el agente de código acabará poniendo rutas de archivo dentro de MOD-06.

**Cerrado el 23/11/2026:** el modelo **no va a Git mientras se itera** (entra en `.gitignore`); para la entrega se versiona **un** archivo de pesos final, junto con el script de entrenamiento, la semilla y `split-prueba.txt`, de modo que la evaluación de RNF-08 sea reproducible. Si ese archivo final resulta demasiado grande para el repositorio, se valora Git LFS **entonces**, con el tamaño real a la vista.

---

### D-19 · N = 1024: dejar de llamarlo SUPUESTO y blindarlo — **bloquea T-16c**

El incremento 2 confirmó dónde vive y cuánto vale: **`puntos_rejilla = 1024`** y **`rango_rejilla_cm1 = [400, 4000]`**, en UT-03 (`backend/utilerias/configuracion/parametros.json`, bloque `procesamiento`), leídos por MOD-04. Quedó marcado `SUPUESTO` porque el 1024 salió del «p. ej.» del diseño de MOD-06 §5.

**El problema no es que fuera un supuesto; es que siga siéndolo.** N no es un dato del mundo que se pueda verificar contra una fuente externa — es una **elección de diseño**. Un supuesto abierto invita a «mejorarlo» más adelante, y cambiarlo después de entrenar **invalida los pesos en silencio**: el modelo seguiría cargando y devolviendo números, solo que equivocados. Así que se cierra como decisión, con su justificación:

- **3600 cm⁻¹ de recorrido (4000–400) entre 1024 puntos ≈ 3.5 cm⁻¹ por punto.** Los espectros reales del proyecto están a 2 y 4 cm⁻¹ de resolución, así que 1024 ni tira resolución que existe ni inventa detalle que no hay. Es el número correcto por una razón, no por inercia.
- **Potencia de dos**, cómoda para las reducciones sucesivas de un CNN 1D (1024 → 512 → 256 …) sin restos.

**Las tres reglas que lo blindan:**

1. **Congelado desde que arranca T-16c.** Antes de entrenar se puede cambiar; después, cambiarlo **obliga a reentrenar**, y eso es una decisión del equipo, no un ajuste de configuración.
2. **El archivo de pesos registra la N con la que se entrenó.**
3. **MOD-06 compara al arrancar** la N de los pesos contra `procesamiento.puntos_rejilla` de UT-03. Si no coinciden, **no carga el modelo**: lo registra y degrada a modo reglas (D-16.4). Un fallo ruidoso en el arranque en lugar de resultados equivocados en producción — es la contramedida concreta al riesgo «consistencia MOD-04 ↔ MOD-06» de MOD-06 §11.

**Cerrado el 23/11/2026:** N = 1024, congelada desde T-16c, con la comprobación de arranque. **Deja de estar marcada `SUPUESTO`** en UT-03 y en `incremento-2.md` §11: pasa a ser una decisión con justificación escrita.

---

### D-20 · Codificación del catálogo (resueltas al cerrar T-14)

Seis decisiones que tomó el agente al implementar T-14 y que el equipo aprueba el 23/11/2026:

| # | Decisión | Veredicto |
|---|---|---|
| 1 | El par ~1600/~1500 de GF-07 va como dos `regiones_acompanantes` de rango puntual (`[1600,1600]`, `[1500,1500]`) con `rol: "par"`; la tolerancia es parámetro de UT-03, no del catálogo | **Aprobada**, con una condición añadida: el lector **valida que un grupo con rol `par` tenga exactamente dos entradas**. Si un dedazo borra una, R-2 se debilita en silencio y hoy nada lo detectaría |
| 2 | `rol` es vocabulario cerrado: `confirmacion` \| `par` \| `indicio` | **Aprobada.** T-15 lee un código en vez de interpretar texto libre, y un rol mal escrito falla al arrancar |
| 3 | `forma` de GF-06 vale `null` porque el diseño no se la asigna; la llave ausente sí se rechaza | **Aprobada.** «No especificado por la fuente» y «se nos olvidó» son cosas distintas y deben distinguirse |
| 4 | La banda de ácidos de GF-01 (2500–3300) es `indicio`, no `confirmacion` | **Aprobada, y es la más fina de las seis.** Si condicionara la detección, **los alcoholes y fenoles quedarían penalizados por no tener la banda de ácido**, que es justo lo que los distingue. Ese `indicio` no es decorativo: **R-4 lo consume** para exigir picos agudos antes de afirmar GF-03 dentro de la envolvente ancha de un ácido |
| 5 | Los subtipos de C=O eran tres y podían estar incompletos | **Era un error del plan, ya corregido:** son **cinco** (sección 4). Añadir aldehído 1720–1740 y ácido carboxílico 1690–1760. La observación sobre la amida se documenta como limitación conocida, no se ensancha GF-05 |
| 6 | `GRUPOS_ESPERADOS = 7` vive en el código, no en la configuración | **Aprobada.** Es el alcance (RF-04), no un parámetro. Configurable, alguien podría ponerlo en 6 y la validación aceptaría un catálogo al que le falta un grupo |

**Correcciones que entran con esto:** los subtipos suben de tres a cinco, y **`enlace_vibracion` de los siete grupos sigue literalmente la columna de la sección 4** — «O–H estiramiento», «N–H estiramiento», … y «estiramiento del anillo» para GF-07. El campo se llama *enlace_vibracion* porque lleva las dos cosas: si guardara solo el símbolo, MOD-07 perdería el modo de vibración al redactar las explicaciones del incremento 4. Si entonces hiciera falta separarlo en dos campos, es un cambio de contrato que se discute ahí, no ahora.

**Tres parámetros nuevos de UT-03 que T-15 necesita** (terreno de D-15, bloque `motor`). Dos de ellos **no se inventan: se miden**, y los cuatro archivos de calibración ya están en `datos/referencia/`:

- **`tolerancia_banda_puntual_cm1`** — el margen alrededor de las bandas de un punto (`par`). Valor de arranque propuesto: **±15 cm⁻¹**, del orden del paso de la rejilla (≈3.5 cm⁻¹) más la dispersión real de posición entre equipos. Se recalibra con el split de validación, como los pesos.
- **`ancho_media_altura_umbral_cm1`** — el corte de **R-1** entre el O–H ancho y el N–H angosto. Se mide en **1-butanol** (O–H ancho por puentes de hidrógeno) y **anilina** (N–H angosto, dos picos), y el umbral se pone entre ambos con su margen.
- **`ancho_pico_agudo_max_cm1`** — el corte de **R-4**, que distingue un pico agudo y resuelto de un hombro ancho antes de afirmar GF-03 dentro de la envolvente de un ácido. Se mide en **ciclohexano** (C–H alifático agudo, sin nada más) y **ácido benzoico** (envolvente ancha de O–H sobre esa misma zona, sin ningún C–H alifático real). Son el par de calibración perfecto: el mismo tramo del espectro, uno con picos de verdad y el otro sin ninguno.

**Las mediciones se hacen sobre el espectro ya normalizado por MOD-04**, no sobre el archivo crudo: es lo que el motor verá en ejecución, y medir en otra escala daría un umbral que no sirve.

#### Resultado de la medición (T-15a, 24/11/2026) — evidencia en `docs/evidencia/d-20-anchos.md`

**R-1 · `ancho_media_altura_umbral_cm1` = 175 cm⁻¹. Aprobado.**

| Compuesto | Grupo | Ancho a media altura |
|---|---|---|
| 1-butanol | GF-01, O–H | 408.9 cm⁻¹ |
| Anilina | GF-02, N–H | 74.0 cm⁻¹ |

Margen de 2.3× a cada lado. Lo que da confianza en el número no es el margen sino la **verificación cruzada**: como R-1 vive en la zona traslapada 3300–3500, se midió cada banda **también en la región del otro grupo**. La anilina da 74.0 en las dos y el butanol varía un 1 % (408.9 / 404.0), es decir **el ancho no depende de dónde se mida**, que es justo lo que necesita una regla que opera en el traslape. El O–H de ácido del ácido benzoico sale aún más ancho (965.9 / 1099.6), en la dirección correcta.

> **Límite conocido del calibrado:** hay **un solo ejemplo de cada clase**, y la anilina es una amina **primaria aromática**, el caso más angosto posible. GF-02 cubre «aminas **y amidas**», y un N–H de amida es bastante más ancho. **No hay ninguna amida en `datos/referencia/`**: el archivo que cerraría ese hueco es `acetamide`, que estaba en la prioridad 2 de D-12. Mientras no exista, R-1 queda calibrada contra el extremo angosto del grupo, y una amida podría clasificarse como O–H. Se revisa con el split de validación (D-15).

**R-4 · `ancho_pico_agudo_max_cm1` = 160 cm⁻¹, medido al 80 % de la altura del pico (no al 50 %). Aprobado, con la definición que lo acompaña.**

El agente no se quedó con los dos archivos prescritos: midió la misma zona en **todos** los espectros reales, y encontró que el método prescrito **no separa las dos clases**.

| Compuesto | ¿C–H alifático? | @50 % | @80 % |
|---|---|---|---|
| Ciclohexano | Sí | 22.9 | 12.6 |
| Tolueno | Sí | 184.4 | 16.5 |
| Acetona | Sí | 145.4 | 19.5 |
| Ciclohexeno | Sí | 44.7 | 22.1 |
| 1-butanol | Sí | 152.9 | 118.3 |
| Ácido benzoico | **No** | 305.3 | 216.5 |
| Anilina | **No** | 760.5 | 639.2 |

Con el corte al 50 %, los dos archivos prescritos sugerían ~84 cm⁻¹ — y ese umbral **habría negado el C–H alifático de la acetona y del tolueno**, que sí lo tienen y miden 145 y 184. El fallo es de la medida, no de la química: cuando la banda es débil, la media altura cae cerca de la línea base y el recorrido se funde con la estructura vecina (en el tolueno cruza en 3101.9, ya dentro del C–H aromático). Al 80 % los siete quedan bien clasificados por un solo corte.

> **El punto apretado es el 1-butanol, en 118.3 frente al corte de 160: 1.35×, la mitad del margen de R-1.** Y tiene sentido que sea él: es el único de los «sí» que además lleva una envolvente ancha de O–H cuya cola pisa la región del C–H — es decir, **es el caso de R-4 en miniatura**. Si al crecer el conjunto ese margen se queda corto, el discriminante mejor no es otro ancho sino el **contraste pico-valle o el número de máximos resueltos** en 2850–2960: el C–H alifático son varios picos estrechos (≈2960, ≈2925, ≈2870) y una envolvente de ácido no tiene ninguno. Eso es literalmente lo que el catálogo quiere decir con «picos agudos». No se implementa ahora; queda anotado para cuando 160 dé problemas.

**Disciplina que vale la pena conservar:** el agente **no fijó el umbral de R-4**, porque pasar del 50 % al 80 % cambia *cómo mide* la regla, y eso es diseño de T-15b, no medición. Dejó el valor en `null` y pidió aprobación de las dos cosas por separado: la definición y el número. Esa frontera es exactamente la correcta.

#### Aprobado por el equipo el 24/11/2026 — qué se aplica antes de T-15b

**1. UT-03, bloque `motor` — los tres valores quedan fijados y dejan de ser `SUPUESTO`:**

| Clave | Valor | Nota |
|---|---|---|
| `tolerancia_banda_puntual_cm1` | **15** | Margen alrededor de las bandas de rango puntual con rol `par` (GF-07) |
| `ancho_media_altura_umbral_cm1` | **175** | R-1. Ancho ≥ 175 → O–H; < 175 → N–H. Medido **al 50 %** de la altura |
| `ancho_pico_agudo_max_cm1` | **160** | R-4. **Medido al 80 % de la altura del pico, no al 50 %.** La definición es parte del parámetro: usar el 50 % aquí invalida el número |

> El nivel de medición **difiere entre las dos reglas a propósito** —R-1 al 50 %, R-4 al 80 %— y no es un descuido: al 50 % la métrica no separaba las clases de R-4, como demuestra la tabla de arriba. Quien implemente no debe «uniformar» los dos niveles.

**2. UT-01 — `enlace_vibracion` de los seis grupos restantes** pasa a seguir literalmente la columna de la sección 4 («O–H estiramiento», «N–H estiramiento», «C–H estiramiento», «C≡N estiramiento», «C=O estiramiento», «C=C estiramiento»). GF-07 ya estaba alineado. Entra **en el commit de T-14**, que aún no está commiteado, para que UT-01 quede cerrado y coherente antes de que T-15b empiece a leerlo.

**3. Pendiente de datos, no bloqueante:** añadir `acetamide` a la lista de descargas de D-12 — es el archivo que cierra el hueco de calibrado de R-1 (ninguna amida en el conjunto actual).

---

### D-21 · Lo que T-15b encontró: el puntaje no separa, y por tres causas distintas

T-15b implementó las cuatro reglas y todas las pruebas de comportamiento quedaron en verde. Pero sobre los ocho espectros reales el motor **acierta 45 de 56 decisiones por grupo y solo 1 de 8 conjuntos completos**. Los siete casos fallidos quedaron como `xfail(strict=True)`: cuentan como fallas y la suite se pondrá roja el día que el motor acierte, para que alguien venga a quitar la marca. Esa es la forma correcta de registrar un problema abierto.

| Compuesto | GF-01 | GF-02 | GF-03 | GF-04 | GF-05 | GF-06 | GF-07 | Qué falla |
|---|---|---|---|---|---|---|---|---|
| ciclohexano | **0.84** | 0.20 | 1.00 | 0.59 | 0.24 | 0.20 | 0.00 | sobra GF-01 |
| acetona | **0.74** | **0.93** | 0.85 | 0.19 | 1.00 | 0.33 | 0.00 | sobran GF-01, GF-02 |
| ácido benzoico | **0.26** | 0.03 | 0.00 | 0.00 | 0.98 | **0.65** | 0.67 | **falta GF-01**, sobra GF-06 |
| tolueno | 0.48 | 0.06 | 0.98 | 0.26 | **0.83** | **0.89** | 0.99 | sobran GF-05, GF-06 |
| ciclohexeno | 0.50 | 0.55 | 1.00 | 0.23 | **0.84** | 0.96 | 0.00 | sobra GF-05 |
| acetonitrilo | **0.92** | 0.33 | 0.99 | 1.00 | 0.51 | 0.01 | 0.00 | sobra GF-01 |
| anilina | **0.87** | 0.94 | 0.22 | 0.04 | 0.52 | **0.86** | 0.89 | sobran GF-01, GF-06 |
| 1-butanol | 0.99 | 0.42 | 0.99 | 0.12 | 0.43 | 0.57 | 0.00 | correcto |

El agente diagnosticó **una** causa: falta una noción de fuerza absoluta. Es correcta y es la principal, pero la tabla muestra **tres problemas separados**, y conviene atacarlos por separado porque un solo parámetro no arregla los tres.

**Causa A · No hay piso de fuerza absoluta → una región vacía puntúa alto.** Es la mayoría de los falsos positivos: GF-01 entre 0.74 y 0.92 en cuatro compuestos **que no tienen ningún O–H**, GF-02 en 0.93 sobre la acetona, GF-05 en 0.83 y 0.84 sobre tolueno y ciclohexeno. El puntaje mide la fuerza de una banda **relativa al desorden del propio espectro**, así que en una región donde solo hay línea base, cualquier ondulación se vuelve «la banda más notable de por aquí». El agente probó las dos escalas posibles sin inventar parámetros (por ruido: 36/56; por prominencia típica: 45/56) y ninguna sirve sola — correcto, el problema no es de escala sino de que **falta un umbral de existencia**.

**Causa B · ~~La ventana de línea base es más angosta que las bandas que tiene que medir.~~ REFUTADA el 24/11/2026 por T-15c.** La hipótesis era que `MARGEN_LINEA_BASE_CM1 = 200` quedaba dentro de una banda de 409 cm⁻¹ y la aplanaba. **Es falsa, por dos motivos medidos:** la ventana efectiva de GF-01 ya era de ±550, porque el margen **se suma a la región ya ensanchada**; y el barrido de márgenes (200 → 3600) sube el ácido benzoico de 0.262 a 0.609 pero sube también a los tres falsos positivos, de modo que los aciertos **bajan** de 45 a 43–44. Ningún margen sirve, y escalarlo con el ancho de la región tampoco. **El margen se queda en 200** — y no debe bajar de 100, porque entonces el hombro del ácido benzoico mediría 74–88 y pasaría R-4.

**La causa real del único falso negativo es otra, y es una decisión nuestra:** el O–H del ácido benzoico **no está en 3200–3550** (la intensidad media ahí es 0.04–0.05). Está en **2500–3200**, que el catálogo declara como región `indicio` — y D-20.4 decidió que un `indicio` **no condiciona la detección**. Al no condicionar, tampoco suma: el O–H más seguro del conjunto vive en una región que el puntaje ignora por diseño. Ver D-22.

**Causa C · ~~R-2 no separa GF-06 de GF-07.~~ REUBICADA el 24/11/2026 por T-15c.** El traslape entre el =C–H del alqueno (3020–3100) y el C–H aromático (3000–3100) **existe y sigue siendo un defecto del plan**, pero **no es lo que produce los tres falsos positivos**. T-15c fue a ver qué pico los gana, y los tres vienen de **fuera de la región de GF-06**: en el ácido benzoico es su propio **C=O en 1684** (4 cm⁻¹ por encima de 1680); en tolueno y anilina es el **anillo, en 1614 y 1618** (6 y 2 cm⁻¹ por debajo de 1620).

No es un problema de reglas de desempate: **es que la búsqueda de picos se sale de la región y acredita al grupo vecino un pico que pertenece a otro**. Por eso **no se añade ninguna regla a R-2 todavía** — primero se corrige la búsqueda. La corrección de R-2 que está anotada en la sección 6 sigue pendiente como defecto real, pero deja de ser urgente.

#### Qué se aprueba

**1. La calibración de fuerza absoluta (causa A) — aprobada, y se mide, no se inventa.** Clave nueva en el bloque `motor`, alimentada por el campo `intensidad` que el catálogo ya tiene:

```
fuerza_minima_relativa: { fuerte: …, media: …, debil: … }
```

como fracción de la banda más intensa del espectro. Como MOD-04 ya normaliza a 0–1, esa fracción es directamente el valor en la escala normalizada. **Se mide con el mismo método de T-15a**, sobre los espectros de referencia, y el equipo ve los números antes de que se escriban. Es el patrón que funcionó con 175 y 160.

**2. Los tres números de definición se mueven a UT-03 (causa B, y regla 1).** `FRACCION_R1 = 0.5`, `FRACCION_R4 = 0.8` y `MARGEN_LINEA_BASE_CM1 = 200` pasan al bloque `motor`, agrupados bajo una subclave que los marque como **definición del método, no como ajuste**. El propio agente dio el argumento decisivo: si el margen cambia, 175 y 160 **dejan de significar lo que significan**. Separar un umbral de su definición es la receta para que alguien cambie uno sin el otro. Juntos y en el mismo archivo, el acoplamiento se ve.

Y el margen **va a cambiar**: 200 no puede medir una banda de 409. Debe **escalar con el ancho declarado de la banda** en vez de ser un número fijo — o como mínimo ser bastante mayor que la banda más ancha del catálogo.

**3. R-2 se corrige (causa C).** Ver la sección 6.

#### Qué NO se hace

**No se mueve ningún umbral para que pase una prueba.** Los siete `xfail` se quitan cuando el motor acierte, no cuando el umbral ceda.

> **Corrección del 24/11/2026.** Este párrafo decía antes que «el 1-butanol pasó R-4 con 0.99 y el corte de 160 no se tocó». **Era falso, y el error es de este documento:** T-15c comprobó que el detector de envolvente mide el C–H del butanol en 163 —por debajo de 175— y concluye que no hay envolvente, de modo que **R-4 nunca llegó a aplicarse**. El caso apretado no se probó: no hay ninguna prueba hoy que lo compruebe. Su pico principal mide 119.5 al 80 %, así que *debería* pasar el corte, pero eso hay que verificarlo, no suponerlo. Se arregla en T-15d.

#### La verdad de referencia: 56 celdas

Hasta ahora esta tabla vivía repartida entre las filas de la sección 9. Se consolida aquí porque es contra lo que se mide todo: qué grupos tiene **de verdad** cada uno de los ocho espectros, por química, no por lo que diga el motor.

| Compuesto | GF-01 | GF-02 | GF-03 | GF-04 | GF-05 | GF-06 | GF-07 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| ciclohexano | — | — | **Sí** | — | — | — | — |
| acetona | — | — | **Sí** | — | **Sí** | — | — |
| ácido benzoico | **Sí** | — | — | — | **Sí** | — | **Sí** |
| tolueno | — | — | **Sí** | — | — | — | **Sí** |
| ciclohexeno | — | — | **Sí** | — | — | **Sí** | — |
| acetonitrilo | — | — | **Sí** | **Sí** | — | — | — |
| anilina | — | **Sí** | — | — | — | — | **Sí** |
| 1-butanol | **Sí** | — | **Sí** | — | — | — | — |

Dos filas merecen una nota porque son contraintuitivas y son justo las que hacen trabajar a las reglas: **el ácido benzoico no tiene C–H alifático** (no hay carbonos sp³ en C₆H₅–COOH) y **la anilina tampoco** (C₆H₅–NH₂). Son los dos casos de R-4 y del negativo cruzado.

#### Secuencia para cerrarlo: T-15c mide, T-15d aplica

Igual que T-15a y T-15b: **nadie toca el puntaje hasta que los números estén sobre la mesa y aprobados.**

- **T-15c — medición, sin cambiar comportamiento.** Mueve los tres números de definición a UT-03 con sus valores actuales (cambio mecánico), comprueba la hipótesis de la causa B barriendo el margen de línea base, y mide la fuerza de la banda de cada grupo en cada uno de los ocho espectros, separando presentes de ausentes contra la tabla de arriba. Reporta y propone.
- **T-15d — aplicación, tras aprobación.** Escribe el margen nuevo y los pisos de fuerza, vuelve a correr las 56 celdas y mira si la causa C se disuelve sola. Solo entonces se decide si R-2 necesita una regla más.

> **Un límite del calibrado que conviene saber de antemano:** el catálogo declara `fuerte` solo para GF-01 y GF-05, `media` para GF-02, GF-03, GF-04 y GF-07, y `media / débil` únicamente para GF-06. Es decir, **el piso de la clase débil se va a calibrar con un solo grupo y un solo espectro verdadero (el ciclohexeno)**. Se usa igual, pero se documenta: es el número menos sostenido de los tres.

---

### D-22 · Lo que T-15c midió, y las siete decisiones que cierra

**El aviso que va primero, porque condiciona todo lo demás.** El propio agente lo escribió: *«todos salen de los mismos 8 espectros con que se evalúan, así que el 54/56 es optimista»*. Tiene razón y hay que tomarlo en serio: **los pisos se están calibrando sobre el mismo conjunto contra el que se mide el acierto.** Eso no es una medida de exactitud, es una medida de ajuste. Dos consecuencias:

1. **Los ocho espectros de referencia quedan quemados como calibración de la vía de reglas.** Ya no son una prueba independiente de ella. Siguen sirviendo como pruebas de regresión —detectan si algo se rompe— pero no dicen cuánto acierta el motor en un espectro que no ha visto.
2. **Cuando Chemotion esté procesado (T-16a), la vía de reglas también necesita su evaluación en datos reservados**, no solo el CNN. Hoy su exactitud fuera de muestra es sencillamente desconocida, y conviene decirlo así en el reporte de RNF-08 en vez de citar el 54/56.

#### Las decisiones

| # | Pregunta | Resolución |
|---|---|---|
| 1 | ¿El margen se queda en 200? | **Sí, y la causa B se cierra como refutada.** El barrido lo demuestra y bajar de 100 rompería R-4 |
| 2 | ¿El `indicio` puede sumar a GF-01 sin penalizar cuando falta? | **Sí — y es un matiz a D-20.4 que corrige una decisión mía.** Ver abajo |
| 3 | Pisos de fuerza | **fuerte 0.10** (condicionado a que la 2 funcione), **media 0.025**, **débil por prominencia 0.029** |
| 4 | ¿Se limita la búsqueda de picos fuera de región? | **Sí, por la vía que propone el agente:** exigir que el piso se cumpla **dentro** de la región. Prohibir del todo rompería el GF-03 de la acetona |
| 5 | ¿R-1 mide el ancho en la banda más prominente de la región? | **Sí.** Es lo único que arregla anilina/GF-01 |
| 6 | ¿Se arregla el detector de envolvente de R-4 y la prueba vacía? | **Sí, en T-15d.** Las dos afirmaban algo que no era |
| 7 | ¿Vale la prueba de no-hardcodeo por AST? | **Sí, pero con la cobertura restaurada.** Ver abajo |

**Sobre la 2 — el matiz a D-20.4.** D-20.4 aprobó que la banda de ácidos de GF-01 fuera `indicio` y no `confirmacion`, con este razonamiento: si condicionara la detección, **los alcoholes y fenoles quedarían penalizados por no tener la banda de ácido**. Ese razonamiento sigue siendo correcto. Lo que estaba mal era la implicación: se confundió **«no debe ser exigida»** con **«no debe sumar»**.

> **`indicio` pasa a significar evidencia aditiva: suma cuando está, es neutra cuando falta.** Asimétrica a propósito. El alcohol no pierde nada por no tener banda de ácido; el ácido gana lo que le corresponde por tenerla. Sin esto **no se cumple CA-05.2**, que exige que el ácido benzoico liste O–H.

La medida que lo respalda: la mediana de la intensidad en 2500–3300 separa los presentes (0.399 y 0.171) de los ausentes (≤ 0.029), un factor 5.9. **Solo hay dos presentes**, así que el número es frágil y se revisa con Chemotion.

**Sobre la 3 — y una precedencia que vale la pena fijar.** D-21 decía que los pisos se medirían **por altura**. La medición mostró que para la clase débil la altura **no separa** (presentes 0.0838, ausentes hasta 0.6734) y la **prominencia sí** (presentes 0.0766, ausentes ≤ 0.0112, quita 3 de 3). Se adopta la prominencia. **Cuando la medición contradice al plan, manda la medición** — y el plan se corrige, que es lo que está pasando aquí.

Firmeza de cada piso, para que nadie los cite como si fueran sólidos: el de la clase **débil** sale de **un solo dato**; el de **media** descansa en un solo contraste dentro de la acetona; el de **fuerte** se apoyaba en un 0.0748 que es *una ladera en 3201, no una banda* — por eso sube a 0.10 si la decisión 2 resuelve el ácido benzoico por la vía del indicio. Y la clase **media** tiene los rangos de presentes y ausentes **completamente solapados** (ambos llegan a 1.0): su piso de 0.025 es casi inerte y no debe esperarse mucho de él.

**Sobre la 7.** La prueba por AST es mejor que la original, porque distingue un número usado de uno citado en un docstring. Pero el agente **sacó `motor_identificacion/` de la cobertura sin avisar**, y esa cobertura estaba pedida expresamente. Se queda la prueba por AST **y** se restaura la cobertura del motor: las dos cosas, no una u otra. El punto de proceso importa más que el técnico — **quitar una verificación que se pidió se avisa antes, no después**.

#### Correcciones al registro

T-15c revisó su propio reporte anterior y corrigió cinco afirmaciones. Dos tienen consecuencias que van más allá de T-15b:

- **La prueba de que «el score cae con la debilidad» era vacía:** un pico aislado de 1.0 y uno de 0.001 dan ambos 1.0. No es solo una prueba mal hecha — **es la causa A enunciada de otra forma**, y estaba delante desde el principio.
- **La penalización suave de R-4 sí bastaba.** D-20.6 aprobó hacer R-4 binaria porque la penalización suave dejaba al ácido benzoico en 0.67; la cifra real es **0.57**, por debajo del umbral. La decisión de que sea binaria **se mantiene** por coherencia con cómo funciona una confirmación ausente, pero **la razón que se dio era falsa** y queda corregida aquí.

También: el vecindario con el que el motor mide no era el mismo de T-15a, y D-21 heredó ese error. El efecto en los anchos es pequeño (118.3 → 119.5 y 216.5 → 230.9) y no cambia ninguna conclusión sobre 175 y 160, pero el acoplamiento se arregla en T-15d.

---

### D-23 · T-15d: 56/56, y lo que ese número no dice

Las siete decisiones se aplicaron **sin mover ningún umbral ni piso**, y el motor pasó de 45/56 a **56/56 celdas y 8/8 conjuntos**. El reparto del mérito, que es lo que pedía la tarea por fases:

| Paso | Aciertos | Conjuntos | Qué arregló |
|---|---|---|---|
| Fase 1 (correcciones) | 45 | 1 | Ninguna celda cambia de veredicto |
| 5 · `indicio` aditivo | 46 | 1 | Ácido benzoico/GF-01: 0.26 → 0.90 |
| 6 · pisos de fuerza | 55 | 7 | 9 falsos positivos, **incluidos los tres GF-06** |
| 7 · R-1 en la banda prominente | **56** | **8** | Anilina/GF-01: 0.85 → 0.37 |

El paso 6 confirmó la reubicación de la causa C: **los tres GF-06 espurios cayeron con el piso dentro de la región, sin añadir ninguna regla a R-2.** Margen final: el presente más bajo es 0.67 y el ausente más alto 0.43, con el umbral en 0.60.

#### Tres reservas sobre ese 56/56

**1. Se midió sobre los mismos ocho espectros que calibraron los pisos.** Ya estaba dicho en D-22 y sigue valiendo: es una medida de ajuste, no de exactitud. **No se presenta como validación en ningún entregable.** El único dato fuera de muestra es el benzonitrilo —convertido a cm⁻¹ en memoria, da exactamente GF-04 y GF-07—, y es **un** espectro.

**2. El puntaje usa el resto del espectro como referencia de ruido, y eso no escala.** T-15d lo midió: en un espectro de dos bandas, **una banda ajena baja un O–H de 1.00 a 0.54**. No ocurre en los ocho reales porque son moléculas simples con pocas bandas. **Los compuestos de Chemotion no lo son**: son productos de síntesis con espectros densos. Es la hipótesis que más probablemente falle al salir de estos ocho, y conviene comprobarla en cuanto T-16a tenga el conjunto procesado — no esperar a que aparezca como un F1 bajo sin explicación.

**3. Bajo el piso, el score cae a 0 de golpe, no decae.** MOD-06 §6 dice que el score «disminuye con la distancia al rango y la debilidad del pico». Con los pisos, por debajo del umbral de existencia el score es **0**, no un valor pequeño. Es defendible —por debajo del piso no hay banda que puntuar— pero **es un refinamiento de §6, no una implementación de §6**, y queda registrado como tal. Dos pruebas se ajustaron para reflejarlo; están nombradas en la evidencia.

#### Decisiones aprobadas

| # | Qué | Resolución |
|---|---|---|
| 1 | R-4 se mide en la cima de la región | **Sí.** Unificar el vecindario rompía el ácido benzoico (un pico en 2835 pasaba de 219.9 a 90.4 y GF-03 subía a 0.79). **Medir donde se calibró** es el principio correcto |
| 2 | El piso del `indicio` se exige a la zona que da la evidencia | **Sí.** La evidencia está en la región de ácido (mediana 0.171); exigirlo en la principal (0.0748) anularía el grupo y daría 55/56 |
| 3 | El `indicio` activa con banda ancha y suma sin señalar pico | **Sí**, con una limitación anotada: **un ácido con C–H alifático intenso podría no activarlo**. Hay que probarlo con un ácido de cadena alifática —`acetic acid`, de la prioridad 2— antes de darlo por bueno |
| 4 | La envolvente de R-4 también exige el piso fuerte | **Sí.** Sin él, ondulaciones de línea base contaban como O–H |
| 5 | Bajo el piso, score 0 | **Sí**, documentado como refinamiento de §6 (reserva 3) |
| 6 | `.gitignore` apunta a `motor-identificacion/modelo/*` con guion | **Arréglalo ya, antes de T-16.** Hoy **los pesos del modelo se commitearían**, contra lo que decidió D-18 |

#### CA-06.2 no se cumple — y va a T-15e, en paralelo con T-16

Con O–H y N–H a la vez, **se suprimen entre sí**: GF-02 queda en 0.44–0.59 en mezclas reales, y en sintéticos un N–H fuerte deja al O–H en 0.12–0.15. El paso 7 **empeoró un caso** (0.87 → 0.12): R-1, al medir la banda más prominente de la región, se volvió estructuralmente de ganador único justo en el traslape — exactamente lo que la sección 6 prohíbe («ajuste de score, nunca exclusión»). Parte del 56/56 se compró con esto.

**CA-06.2 es criterio del incremento 4, pero su precondición es de MOD-06:** si el motor no reporta los dos grupos, MOD-05 no tiene qué resaltar y el criterio es inalcanzable. Como **T-16 no depende de T-15 en absoluto**, no hay razón para diferirlo: **T-15e corre en paralelo con T-16a**, con otra persona.

**H8: CERRADO** el 24/11/2026. Su criterio se cumple (acetona → GF-05 = 1.00, pico en 1719.6 dentro de su región) y los ocho espectros cuadran. Se cierra **con CA-06.2 anotado como pendiente** y sin presentar el 56/56 como validación: eso lo dirá RNF-08.

> **Fallo de proceso que hay que corregir antes de seguir.** El agente trabajó T-15c con el plan v2.2 en disco y T-15d también, tomando los valores del chat porque **el plan actualizado nunca se subió al repositorio**. Funcionó por poco y porque alguien iba pasando los números a mano. Es exactamente lo que la regla de oro del proyecto prohíbe: las decisiones viven en los documentos, no en el chat. **Antes de abrir cualquier conversación nueva, la v2.4 tiene que estar en `docs/plan/` y reemplazada en el Proyecto.**

---

## 2. Alcance y fronteras del incremento 3

**Dentro:**

- UT-01, el catálogo de los 7 grupos, como fuente única (T-14).
- MOD-06 completo: vía de reglas (T-15), vía ML (T-16), fusión y umbral (T-17).
- MOD-01 ampliado: la lista ordenada con su confianza (T-18) y el aviso de «sin detecciones confiables» o de fallo del motor (T-19).
- El trabajo de datos que lo habilita (T-3R).
- CA-05.1 … CA-05.4, CA-08.1 … CA-08.3, RNF-08 y la primera medición real de RNF-02.

**Fuera, explícitamente:**

| Qué | Dónde va |
|---|---|
| Las plantillas de explicación y el texto educativo | T-20, T-21, T-22 — incremento 4. **T-20 puede adelantarse aquí**: solo depende del catálogo (T-14), y el Plan V3 ya lo autoriza |
| Resaltar la región y el pico sobre la gráfica | T-23, T-24 — incremento 4. MOD-06 **sí entrega** `region_cm1` y `pico_cm1`; quien los pinta es MOD-05, después |
| El reporte en PDF | T-25 … T-27 — incremento 5 |
| Los subtipos de C=O (cetona ~1715, éster 1735–1750, amida 1630–1700 …) | Son **datos del catálogo** para las explicaciones del incremento 4. En el incremento 3 **GF-05 es una sola detección**: RF-04 pide los siete grupos, no sus subtipos |
| La banda «posible» 0.4–0.6 | Fuera por D-15, salvo que el equipo decida lo contrario |
| Identificar la molécula completa, cuantificar, otras técnicas | Fuera del alcance del proyecto (Requerimientos §5) |

**La frontera que más hay que cuidar:** MOD-06 es **zona aislada**. Recibe el vector normalizado y el eje según el contrato de MOD-06 §5, y nada más. No ve el archivo, no ve su nombre, no ve el veredicto de MOD-03, no abre archivos en inferencia, no sale a la red. Si una tarea de este incremento necesita algo que no está en ese contrato, **la tarea está mal planteada** — hay que replantearla, no ensanchar el contrato.

---

## 3. Módulos, archivos y dependencias

| Módulo / utilería | Archivos previstos | Necesita de | Entrega a | Tarea |
|---|---|---|---|---|
| **UT-01 · Catálogo** | `datos/catalogo/grupos.json` + su lector de solo lectura | — | MOD-06 (y MOD-07, MOD-08 después) | T-14 |
| **UT-03 · Configuración** (se amplía) | `backend/utilerias/configuracion` | — | MOD-06 | T-15 / T-17 |
| **UT-02 · Mensajes** (se amplía) | `backend/utilerias/mensajes` | — | MOD-06, MOD-01 | T-19 |
| **MOD-06 · reglas** | `motor_identificacion/reglas` | T-10 (vector), UT-01 | fusión | T-15 |
| **MOD-06 · modelo** | `motor_identificacion/modelo` | T-10, UT-01 (orden de etiquetas) | fusión | T-16 |
| **MOD-06 · inferencia** | `motor_identificacion/inferencia` | reglas + modelo + UT-03 | MOD-01, y MOD-07 después | T-17 |
| **Entrenamiento** (fuera de la app) | `herramientas/entrenamiento/` | MOD-04 (normalización), dataset | el archivo de pesos | T-16 |
| **MOD-01 · interfaz** (se amplía) | `frontend/interfaz`, `frontend/servicios` | contrato de MOD-06 | usuario | T-18, T-19 |

**Dos reglas de dirección que evitan el error que ya mordió en el incremento 1:**

1. **El script de entrenamiento importa de la app; la app nunca importa del script.** `herramientas/entrenamiento/` usa la normalización **real de MOD-04**, no una copia. Si el entrenamiento normaliza distinto que producción, el modelo funciona en el cuaderno y falla en la app, y el síntoma aparece lejísimos de la causa. Es el mismo riesgo que MOD-06 §11 llama «consistencia MOD-04 ↔ MOD-06», y la misma lección de D-2.
2. **Nadie lee `grupos.json` por su cuenta.** Todos piden los datos a UT-01 (persistencia v2). Un número de región escrito a mano en la vía de reglas es un defecto, no un atajo.

---

## 4. Los números del catálogo (base de UT-01 y de la vía de reglas)

Tomados de Requerimientos V3.2 §6.2 y de MOD-06 §4. **Este es el único lugar del incremento donde estos números se escriben**; de aquí pasan a `grupos.json` y de ahí los lee todo lo demás.

| ID | Grupo | **Enlace / vibración** | Región principal (cm⁻¹) | Región acompañante (cm⁻¹) | Intensidad / forma |
|---|---|---|---|---|---|
| GF-01 | O–H (alcoholes, fenoles y ácidos) | O–H estiramiento | 3200–3550 | ácidos: 2500–3300 | Fuerte, ancha |
| GF-02 | N–H (aminas y amidas) | N–H estiramiento | 3300–3500 | — | Media; más angosta que O–H; 2 picos (primarias), 1 (secundarias) |
| GF-03 | C–H alifático (sp³) | C–H estiramiento | 2850–2960 | — | Media; picos **agudos** justo por debajo de 3000 |
| GF-04 | C≡N (nitrilos) | C≡N estiramiento | 2210–2260 | — | Media; pico agudo en zona casi siempre vacía |
| GF-05 | C=O (carbonilo) | C=O estiramiento | 1670–1780 | — | Fuerte y aguda; suele ser la señal más evidente |
| GF-06 | C=C (alquenos) | C=C estiramiento | 1620–1680 | =C–H 3020–3100 | Media / débil (**el diseño no le asigna forma**: el catálogo la deja en `null`, que es distinto de que falte) |
| GF-07 | Anillo aromático | **estiramiento del anillo** | 1450–1600 (bandas ~1600 y ~1500) | C–H aromático 3000–3100 | Media; **par** de bandas |

**Subtipos de C=O (GF-05) — los cinco de MOD-06 §4, informativos para el incremento 4:** cetona ~1715 · aldehído 1720–1740 · éster 1735–1750 · ácido carboxílico 1690–1760 · amida 1630–1700.

> **Corrección del 23/11/2026 (error de este plan, no del código).** La versión 1.0 de este documento citaba los subtipos abreviados y con puntos suspensivos en la sección 2, y omitía la columna «Enlace / vibración» de MOD-06 §4. Un plan que es fuente de verdad no puede abreviar una lista: **ambas cosas quedan completas arriba**.
>
> **Y una inconsistencia real entre los documentos aprobados, que conviene conocer:** el subtipo **amida, 1630–1700**, cae parcialmente **por debajo** de la región principal de GF-05 (1670–1780). Una amida cuyo C=O esté en, digamos, 1650 cm⁻¹ queda **fuera de la región donde GF-05 se detecta**, y además cae dentro de GF-06 (1620–1680). La regla **R-2 impide que se reporte como alqueno** —una amida no tiene =C–H en 3020–3100, así que el score de GF-06 queda acotado—, de modo que el efecto es **una omisión, no un falso positivo**, que es el fallo menos grave de los dos. **No se ensancha GF-05**: cambiar un rango de §6.2 es un cambio de alcance. Queda documentado como limitación conocida y va a la revisión química de T-20.

**Orden canónico de las etiquetas: GF-01, GF-02, GF-03, GF-04, GF-05, GF-06, GF-07.** Ese es el orden del vector binario de 7 posiciones del etiquetado y de la salida del CNN. Queda fijado aquí porque **T-16 y T-14 tienen que coincidir** y son tareas distintas, posiblemente de personas distintas: si el orden se decide dos veces, el modelo acierta con las etiquetas cruzadas y nadie lo nota hasta que el ácido benzoico reporte un nitrilo.

**Nota documental menor** (no es una decisión): para el C–H aromático de GF-07, Requerimientos §6.2 da 3000–3100 y MOD-06 §4 menciona «~3030». Se usa el rango de Requerimientos; 3030 es la posición típica dentro de él. Los subtipos de C=O de MOD-06 §4 se cargan como `subtipos` informativos para el incremento 4.

---

## 5. Contratos

### UT-03 → MOD-06
El umbral y los pesos, según D-15: `umbral_confianza`, `pesos.wR`, `pesos.wML`, validados al cargar.

### UT-01 → MOD-06
Por cada grupo: `id`, `nombre`, `enlace_vibracion`, `region_cm1: [min, max]`, `regiones_acompanantes: [ { rango, rol } ]`, `intensidad`, `forma`, `pista`, `subtipos` (informativo). Más la `version` del catálogo y el orden canónico. Solo lectura.

### MOD-04 → MOD-06  *(fuente única: MOD-06 §5, ya fijada en el incremento 2 por T-10)*
- `intensidad`: **absorbancia, línea base corregida, normalizada 0–1**, en **1024 puntos** (D-19).
- `eje_cm1`: el eje ordenado de **4000 a 400 cm⁻¹**, repartido de forma pareja.
- `rango_medido_cm1`: `[min, max]` — el tramo que **de verdad midió el archivo**.
- `unidad_original`: absorbancia, transmitancia o porcentaje. Informativa para MOD-06.
- Todo redondeado a 6 decimales.
- **Nunca el archivo, ni su nombre, ni su formato.**

> #### El relleno de ceros: el detalle que más fácil rompe el modelo
>
> El incremento 2 lo dejó advertido y conviene subrayarlo: **fuera de `rango_medido_cm1` la intensidad vale 0, y ese 0 es relleno, no absorbancia cero.** Un espectro que solo cubre el mínimo exigido por §6.1 (1400–3700) llega con cerca del 40 % del vector relleno; uno que cubre 400–4000 llega sin nada de relleno. Son dos vectores muy distintos para la misma química.
>
> **Para la vía de reglas (T-15):** un cero de relleno **no es «no hay pico»**, es «no se midió». Como §6.1 garantiza 1400–3700 y **las regiones de los siete grupos caben dentro de ese intervalo** —por eso se eligió ese mínimo—, en un archivo válido ninguna región queda sin medir. Aun así, T-15 comprueba contra `rango_medido_cm1` antes de puntuar: si una región cayera fuera, el grupo se marca **no evaluable**, no «ausente». La diferencia importa en el incremento 4, cuando haya que explicarlo.
>
> **Para la vía ML (T-16), que es donde de verdad muerde:** si unos espectros del conjunto llevan relleno y otros no, la red puede aprender **la forma del relleno** en vez de la química — y si por azar los nitrilos del conjunto vienen de archivos de rango corto, aprenderá que «relleno ancho ⇒ nitrilo». Es un atajo invisible que infla las métricas de entrenamiento y se derrumba en producción. **Regla: el CNN recibe únicamente la ventana 1400–3700 cm⁻¹**, que §6.1 garantiza medida en todo archivo válido, de modo que el relleno nunca entra al modelo. La vía de reglas sí puede usar la rejilla completa, porque mira regiones concretas. Esto no cambia el contrato: MOD-06 recorta por dentro.

### MOD-06 → MOD-01 / MOD-07  *(MOD-06 §5, con los dos añadidos de D-16)*

```
{
  "detecciones": [
    { "grupo": "GF-05", "confianza": 0.94,
      "region_cm1": [1670, 1780], "pico_cm1": 1715,
      "evidencia": { "regla": 0.97, "ml": 0.91 } }
  ],
  "sin_detecciones": false,
  "umbral": 0.6,
  "modo": "hibrido"
}
```

- `detecciones` va **ordenada de mayor a menor confianza** (RF-04).
- `region_cm1` y `pico_cm1` **vienen siempre de la vía de reglas**, nunca del modelo (MOD-06 §2 y §6). El modelo aporta robustez, no posición: no sabe dónde está el pico.
- `pico_cm1` puede ser `null` — un grupo detectado sin posición exacta de pico es un caso previsto (CA-06.3, incremento 4).
- `evidencia.ml` puede ser `null` (modo reglas). **Los consumidores lo tratan como anulable desde ahora.**
- Sin detecciones: `detecciones: []` y `sin_detecciones: true`. **Es un resultado normal, no un error.**

### MOD-06 → UT-02
Códigos nuevos, con su mensaje y su público:

| Situación | Para el usuario | Nivel |
|---|---|---|
| Fallo interno del motor (CA-05.4) | «No fue posible completar el análisis; intenta de nuevo» — **sin detalles técnicos**, y conservando el archivo cargado | Error |
| Modelo no disponible (D-16.4) | Nada, o un aviso discreto: el análisis **sigue** en modo reglas | Registro interno |
| Vector inválido en el endpoint (D-17) | Mensaje de error con motivo y acción | Error |
| Sin detecciones confiables (CA-08) | «No se encontraron detecciones confiables» + sugerir revisar la calidad del espectro | **No es error**: viaja en el resultado |

---

## 6. Reglas de desempate y trampas conocidas

El riesgo n.º 6 de Requerimientos §13 está **abierto**: el traslape O–H / N–H y C=C / aromático. Aquí se cierra con reglas concretas. Las tres primeras son las que deciden si el motor es químicamente honesto.

**R-1 · O–H (GF-01) vs N–H (GF-02), traslapados en 3300–3500.** Desempate por **ancho de banda** (el rasgo que el propio catálogo usa): O–H es ancha e intensa; N–H más angosta, y en aminas primarias son dos picos. Se mide el ancho a media altura.

> **Y la regla no es excluyente.** Son dos etiquetas, no una elección: CA-06.2 espera un espectro con **O–H y N–H detectados a la vez**. El desempate **ajusta los scores**, nunca suprime uno de los dos. Un desempate que elija ganador rompe CA-06.2.

**R-2 · C=C (GF-06) vs anillo aromático (GF-07).** Sus regiones principales son vecinas (1620–1680 y 1450–1600) y ambos grupos son débiles. El desempate está en la **banda acompañante**, que es lo que de verdad los distingue:

- GF-07 exige el **par** de bandas (~1600 **y** ~1500) **más** C–H aromático en 3000–3100.
- GF-06 exige su **=C–H en 3020–3100**.
- Si la banda acompañante no está, el score se **acota por debajo del umbral** en vez de reportar el grupo.

> **Corrección del 24/11/2026 (defecto de este plan, detectado por los datos de T-15b).** Tal como estaba escrita, **R-2 no separa GF-06 de GF-07**: el =C–H del alqueno (3020–3100) y el C–H aromático (3000–3100) **se solapan casi por completo**, así que cualquier aromático satisface la confirmación del alqueno. Resultado real: GF-06 en 0.65, 0.89 y 0.86 sobre ácido benzoico, tolueno y anilina, que no tienen C=C de alqueno. R-2 sí protege a GF-07, porque a ese le exige el **par** completo además del C–H; el desprotegido es GF-06.
>
> **La banda compartida no puede ser el discriminante.** Tres salidas, a decidir por el equipo:
>
> 1. **Condicionar GF-06 a GF-07** — si GF-07 está presente con fuerza, la señal aparente de GF-06 en 1620–1680 se atribuye preferentemente al anillo y su score se acota. Barato y resuelve los tres casos de la tabla. **Riesgo:** un compuesto que tenga los dos de verdad —el caso del estireno— quedaría subestimado. Como el estireno se descartó por unidades, hoy **no hay ningún espectro en el conjunto que tenga ambos**, así que esta regla no se puede validar en las dos direcciones. Eso, por sí solo, es un argumento para conseguir ese archivo.
> 2. **Exigir a GF-06 fuerza absoluta en su región principal**, no solo la acompañante — es decir, dejar que la causa A haga el trabajo. Si las bandas de 1620–1680 en tolueno y anilina son débiles en términos absolutos, el piso de fuerza las elimina sin necesidad de una regla nueva. **Es la opción más limpia si funciona**, y se sabrá al medir `fuerza_minima_relativa`.
> 3. **Aceptar el traslape y documentarlo** como limitación: GF-06 es uno de los dos grupos que el diseño ya anticipa con F1 bajo (MOD-06 §8).
>
> **Recomendación: medir primero la causa A y volver a mirar la tabla.** Si la opción 2 basta, no se añade ninguna regla; si no basta, se discute la 1 con un espectro que tenga ambos grupos para poder validarla.

**R-3 · La contaminación de CCl₄ de la acetona — la trampa ya documentada, convertida en prueba.** El archivo real de acetona declara `$$SPECTRAL CONTAMINATION DUE TO CCl4 AROUND 1550`. Esos 1550 cm⁻¹ caen dentro de 1450–1600, que es **GF-07**, y la acetona **no tiene anillo aromático**. Un «pico dentro del rango» ingenuo reporta un aromático inexistente.

> Con R-2 no debería pasar: no hay par de bandas ni C–H aromático. Por eso se añade una prueba de regresión: **acetona → GF-05 detectado y GF-07 NO detectado.** CA-05.1 no lo exige (solo pide detectar C=O), así que es una prueba **añadida**; vale la pena porque convierte un hallazgo que ya costó encontrar en una red de seguridad permanente.

**R-4 · El O–H de ácido pisa el C–H alifático.** GF-01 en ácidos cubre 2500–3300, y GF-03 vive en 2850–2960: **dentro** de esa banda. El ácido benzoico es el caso: su envolvente ancha de O–H ocupa la zona de C–H, pero el ácido benzoico **no tiene C–H alifático** (no hay carbonos sp³ en C₆H₅–COOH). Un detector ingenuo reportaría GF-03 en un compuesto que no lo tiene, y en el incremento 4 la capa educativa tendría que explicar un grupo falso.

> Regla: dentro de una envolvente ancha de O–H, afirmar GF-03 exige **picos agudos y resueltos**, no un hombro ancho. Es exactamente el rasgo que el catálogo le asigna a GF-03 («picos agudos justo por debajo de 3000»). CA-05.2 lista O–H, C=O y aromático para el ácido benzoico; se añade la verificación de que **GF-03 no aparece**.

**R-5 · El signo de `##DELTAX=` — cerrado, no reabrir.** El archivo real de ácido benzoico trae `+1` cuando el eje baja. Se resolvió en el incremento 2: MOD-04 deduce la dirección comparando `##FIRSTX=` con `##LASTX=`. Se anota aquí solo para que nadie lo vuelva a tocar desde MOD-06.

**R-3 y R-4 quedaron confirmadas por el equipo el 23/11/2026** y entran como pruebas de regresión obligatorias de la sección 9, aunque ningún CA las exija.

---

## 7. Orden de trabajo, hitos y reparto

### Secuencia

```
T-3R (datos) ──────────────────────────────────────────────┐  en paralelo a todo
                                                            │
T-14 (catálogo) ──┬──► T-15 (reglas) ──────────┐           │
                  │                             ├──► T-17 ──┼──► T-18 ──► T-19
                  └──► T-16a→b→c→d (vía ML) ────┘           │
                                                            │
        [T-20, plantillas del incremento 4, adelantable] ───┘
```

| Hito | Se cierra cuando | Evidencia |
|---|---|---|
| **H8** | UT-01 entrega los 7 grupos y la vía de reglas detecta C=O con su región en la acetona | Catálogo + prueba de cobertura + resultado de reglas sobre espectros reales y sintéticos · **24/11/2026: ABIERTO.** Su criterio literal se cumple (acetona → GF-05 = 1.00, pico en 1719.6 dentro de 1670–1780), pero su evidencia pide el resultado sobre espectros reales y ese resultado es 1 de 8. El plan apuesta a que una vía de reglas sólida convierte el plan B en opción viable; con 1 de 8 todavía no lo es. Se cierra al resolver D-21 |
| **H9** | La vía ML tiene métricas sobre el conjunto de prueba independiente **y** la fusión con umbral funciona (CA-05.3) | Tablas de RNF-08 (las dos de D-13) + pruebas de umbral con confianzas simuladas |
| **H10** | MOD-01 muestra la lista con su confianza y el aviso / el fallo; **el incremento 3 es demostrable** | CA-05.1, 05.2, 05.4, CA-08.1–08.3 + medición de RNF-02 |

### Paralelización y cuellos de botella

- **T-16 arranca el primer día, no después de T-15.** Es la tarea más pesada de toda la aplicación (esfuerzo **Alto** en el Plan V3) y está en la ruta crítica. Solo necesita de T-14 el orden canónico de las etiquetas, que es gratis.
- **T-3R arranca antes que todo.** Sin los espectros de GF-04 y GF-06 (D-14) ni el dataset (D-12), T-15 se prueba a medias y T-16 no arranca. Es trabajo de datos y de química, no de código: **no se delega al agente de código.** Elegir el espectro correcto (fase, rango, puntos) es una decisión química; un agente que baje «el primer resultado» traerá un archivo que no sirve.
- **T-15 va primero en valor.** Identifica de punta a punta por sí sola — es la Fase 1 del diseño y es el plan B ya construido. Si T-15 queda sólida, el plan B deja de ser un riesgo y pasa a ser una opción.
- **T-20 se puede adelantar** desde el incremento 4: solo depende de T-14.

### Reparto

El Plan V3 asigna los responsables de los incrementos 2 a 5 **al arrancar cada uno**, y advierte expresamente la sobrecarga de este: *T-16 es la tarea más pesada y está en la ruta crítica; asignarla a una persona dedicada desde el inicio, mientras la otra avanza T-14, T-15, T-18 y T-19.*

| Tarea | Responsable | Revisa | Esfuerzo (Plan V3) |
|---|---|---|---|
| T-3R | Por asignar | Por asignar | Medio |
| T-14 | Por asignar | Por asignar | Medio |
| T-15 | Por asignar | Por asignar | Medio-Alto |
| T-16 (a–d) | Por asignar — **dedicada** | Por asignar | **Alto** |
| T-17 | Por asignar | Por asignar | Medio |
| T-18 | Por asignar | Por asignar | Bajo-Medio |
| T-19 | Por asignar | Por asignar | Medio |

---

## 8. Tareas

### T-3R · Datos y espectros del incremento 3 — `datos/referencia/`, `datos/dataset/`

- **Objetivo:** cerrar los dos grupos sin espectro (GF-04, GF-06), armar el conjunto de entrenamiento y **congelar** el subconjunto de prueba independiente.
- **Bloqueada por:** D-12 y D-14.
- **Insumos:** NIST WebBook — las entradas exactas de D-14 (benzonitrilo `C100470`, ciclohexeno `C110838`, estireno `C100425`) y la lista de compuestos de D-12; los tres espectros ya descargados en T-0R; los términos de uso de NIST y SDBS.
- **Partes:**
  1. Los espectros de referencia nuevos, en **fase condensada** y con unidad admitida, cada uno con su nota de origen completa.
  1-bis. **Cobertura verificada el 23/11/2026:** el tercer archivo de T-0R es `62-53-3` (**anilina**), así que **GF-02 queda cubierto** y los siete grupos tienen al menos un espectro. La tabla de cobertura y los huecos que quedan están en D-12.
  2. El conjunto de entrenamiento según la opción elegida en D-12, con su `indice.csv` (identificador, CAS, fase, rango, puntos, origen, 7 etiquetas, split).
  3. El split 70/15/15 **sin que un compuesto caiga en dos conjuntos**, y `split-prueba.txt` congelado con su suma de verificación.
- **Terminado:** los espectros nuevos están en `datos/referencia/` con su nota; `indice.csv` y `split-prueba.txt` están versionados; los espectros del dataset **no** están en el repositorio; los términos de uso quedaron revisados y anotados.
- **Fronteras:** no es trabajo del agente de código. El etiquetado se deriva de la estructura, no del espectro: si hay duda química sobre una etiqueta, el compuesto se deja fuera en vez de adivinar.

### T-14 · Catálogo de los 7 grupos — UT-01 · `datos/catalogo/grupos.json`

- **Objetivo:** fuente única de los 7 grupos, en solo lectura.
- **Insumos:** la tabla de la sección 4 de este plan (Requerimientos §6.2 + MOD-06 §4).
- **Predecesora:** ninguna.
- **Terminado:** los 7 grupos con ID, nombre, región principal, regiones acompañantes, intensidad, forma y pista; el orden canónico fijado; subtipos de C=O cargados como informativos; leído solo a través de UT-01.
- **Pruebas:** cobertura — los 7 grupos existen y ninguno le falta región ni rasgo. Prueba de no-«hardcodeo»: ningún número de región aparece fuera del catálogo.
- **Fronteras:** **sin textos de explicación** (son T-20, incremento 4). El catálogo es datos, no lógica: no decide nada.

### T-15 · Vía de reglas — `motor_identificacion/reglas`

- **Objetivo:** detectar picos y compararlos con el catálogo; devolver un score en [0, 1] por grupo, **con su región y su pico**.
- **Insumos:** vector normalizado de T-10, catálogo de T-14, reglas R-1 a R-4 de la sección 6.
- **Predecesoras:** T-10, T-14.
- **Terminado:** score por grupo; el score decrece con la distancia al rango y con la debilidad del pico (MOD-06 §6); las reglas de desempate aplicadas como **ajuste de score**, no como exclusión; con la acetona detecta C=O en 1670–1780 cm⁻¹.
- **Pruebas:** espectros sintéticos (un pico en 1715 → GF-05 con su región; sin picos → nada); la acetona real → GF-05 sí, GF-07 no (R-3); el ácido benzoico real → O–H, C=O y aromático, y GF-03 no (R-4); el ciclohexeno → GF-06 (banda débil); el benzonitrilo → GF-04 y GF-07.
- **Fronteras:** cero aprendizaje automático aquí; cero texto de explicación; no toca UT-03 más allá de leer lo que necesite. Debe ser **determinista**: la misma entrada da el mismo score siempre.

### T-16 · Vía ML (CNN 1D multi-etiqueta) — `motor_identificacion/modelo` + `herramientas/entrenamiento/`

La tarea más pesada del proyecto. Se parte en cuatro para que tenga hitos propios y no sea un bloque opaco de semanas (refinamiento autorizado por el Plan V3; no cambia su alcance ni su ID).

**T-16a · Conjunto de datos y etiquetado.** Bloqueada por D-12 y T-3R. Terminado: el dataset existe, etiquetado en el orden canónico, con `indice.csv` y el split congelado, y el support de cada clase **contado y escrito** (es lo que explicará después los F1 bajos).

**T-16b · Paridad de preprocesamiento.** Objetivo: el entrenamiento usa **la normalización real de MOD-04**, no una copia. Terminado: una prueba demuestra que un espectro procesado por la ruta de entrenamiento y por la ruta de producción da el **mismo vector**. Es la prueba que previene el riesgo «consistencia MOD-04 ↔ MOD-06» de MOD-06 §11. Bloqueada por el valor real de N (D-17).

**T-16c · Entrenamiento.** Insumos: T-16a, T-16b, UT-01 (orden de etiquetas). Terminado: salida sigmoide de 7 probabilidades independientes (multi-etiqueta, no multi-clase); **semilla fija** y registrada; el desbalance de clases atendido explícitamente (ponderación por clase o, como mínimo, reportado con su support); el archivo de pesos en `motor_identificacion/modelo/` según D-18. Fronteras: la arquitectura concreta la decide quien implemente **dentro de este contrato**; lo que el plan fija es la entrada, la salida, la semilla, el split y las métricas. No se toca `split-prueba.txt`.

**T-16d · Evaluación (RNF-08).** Terminado: las **dos** tablas de D-13 — la vía ML sola (sigmoide en 0.5) y el motor completo (post-fusión, umbral 60 %) — con precisión, recall, F1 y support de los siete grupos, macro-F1 y matriz de confusión uno-contra-resto, sobre el subconjunto de prueba independiente. Evidencia en `docs/evidencia/rnf-08.md`, con la semilla y la suma de verificación del split. Si un grupo de la puerta falla, se escribe y se escala a D-16. **El subconjunto de prueba se usa una sola vez.**

### T-17 · Fusión y umbral — `motor_identificacion/inferencia`

- **Objetivo:** `conf = wR·score_regla + wML·prob_ml` y aplicar el umbral.
- **Insumos:** T-15, T-16, umbral y pesos de UT-03 (D-15).
- **Predecesoras:** T-15, T-16 (o solo T-15 si se activó el plan B).
- **Terminado:** confianza por grupo; umbral aplicado según la regla aritmética de D-15; resultados ordenados de mayor a menor; `sin_detecciones` cuando la lista queda vacía; la región y el pico tomados **de la vía de reglas**; `modo` y `evidencia.ml` según D-16; **funciona con `wML = 0` sin cambiar el contrato**.
- **Pruebas:** CA-05.3 con confianzas simuladas (60 % aparece, 59 % no); CA-08.2 (máximo 59 % → aviso); `wML = 0` reproduce exactamente el score de reglas; cuando regla y ML coinciden la confianza sube y cuando discrepan baja (MOD-06 §8); el orden descendente se mantiene con empates.
- **Fronteras:** no implementa la banda «posible» (D-15).

### T-18 · Lista ordenada con su confianza — MOD-06 → MOD-01

- **Objetivo:** que el usuario vea los grupos detectados con su confianza en porcentaje, de mayor a menor.
- **Insumos:** T-17, el contrato HTTP de D-17.
- **Terminado:** CA-05.1 (acetona → C=O con confianza ≥ 60 % en porcentaje) y CA-05.2 (ácido benzoico → O–H, C=O y aromático en orden descendente). El porcentaje mostrado **sale del mismo número que decidió el veredicto** (D-15).
- **Fronteras:** sin explicaciones y sin resaltado — incremento 4. No se muestra el código de error interno al usuario.

### T-19 · «Sin detecciones confiables» y fallo del motor

- **Objetivo:** cubrir los dos caminos que no son el feliz, y no confundirlos.
- **Insumos:** T-17, UT-02, MOD-01.
- **Terminado:**
  - CA-08.1 (espectro ruidoso, ningún grupo al 60 % → aviso, sugerencia de revisar la calidad, **ninguna** fila de grupo), CA-08.2 y CA-08.3 (solo línea base → aviso, sin detenerse de forma abrupta).
  - CA-05.4 (fallo interno simulado → «No fue posible completar el análisis; intenta de nuevo», **sin detalles técnicos**, conservando el archivo cargado).
  - Modelo ausente → arranca y responde **en modo reglas**, registrándolo, sin mensaje de error (D-16.4).
- **Fronteras:** `sin_detecciones` **no** viaja por la ruta de errores de UT-02; va en el resultado. Confundir las dos cosas produce un «error» donde el sistema en realidad está siendo honesto.

---

## 9. Plan de pruebas

Las filas del Plan V3 Paso 6 para el incremento 3, más las añadidas por este plan (marcadas **+**).

| CA / RNF | Tipo | Datos o condición | Resultado esperado | Nivel | Evidencia |
|---|---|---|---|---|---|
| CA-05.1 | Normal | Espectro de referencia de acetona | Detecta C=O con confianza ≥ 60 % en porcentaje | Integr. (MOD-06) | Resultado + espectro |
| CA-05.2 | Normal | Espectro de referencia de ácido benzoico | Lista O–H, C=O y aromático, de mayor a menor confianza | Integr. (MOD-06, MOD-01) | Captura de la lista |
| CA-05.3 | Límite | Confianzas simuladas de 60 % y 59 % | El de 60 % aparece; el de 59 % no | Unit (MOD-06, UT-03) | Resultado + confianzas |
| CA-05.4 | Error | Fallo interno simulado (mock) | Mensaje genérico, sin detalles técnicos, archivo conservado | Unit con mock | Captura + registro |
| CA-08.1 | Normal | Espectro ruidoso, ningún grupo al 60 % | Aviso, sugerencia, lista vacía | Integr. | Captura del aviso |
| CA-08.2 | Límite | Máxima confianza = 59 % | Aviso de sin detecciones confiables | Unit | Resultado + entrada |
| CA-08.3 | Error | Espectro válido con solo línea base | Informa sin detenerse de forma abrupta | Integr. (MOD-06, MOD-04) | Captura + registro |
| **RNF-08** | Métrica | Subconjunto de prueba **independiente y congelado** | Las dos tablas de D-13; puerta cumplida en GF-01, GF-04, GF-05; los siete reportados | Evaluación | `docs/evidencia/rnf-08.md` + semilla + suma del split |
| **+ RNF-02** | Rendimiento | Análisis de un espectro, modelo ya cargado, CPU | ≤ 5 s desde «Analizar» (MOD-06 §9) | Integr. | Tiempos medidos, no estimados |
| **+ R-3** | Regresión | Acetona real (con contaminación de CCl₄ en ~1550) | GF-05 detectado y **GF-07 no** | Unit (reglas) | Resultado + nota del archivo |
| **+ R-4** | Regresión | Ácido benzoico real | O–H, C=O, aromático detectados y **GF-03 no** | Unit (reglas) | Resultado |
| **+ R-1** | Límite | Espectro con O–H y N–H | **Ambos** detectados, ninguno suprimido (prepara CA-06.2) | Unit (reglas) | Resultado |
| **+ GF-04** | Normal | Benzonitrilo | GF-04 detectado; GF-07 también | Integr. | Resultado + espectro |
| **+ GF-06** | Límite | Ciclohexeno (banda débil) | GF-06 detectado | Integr. | Resultado + espectro |
| **+ T-16b** | Paridad | Un mismo espectro por la ruta de entrenamiento y por la de producción | Vectores **idénticos** | Unit | Comparación |
| **+ D-16.4** | Degradación | Archivo de pesos ausente | Arranca y responde en modo reglas; lo registra; sin error al usuario | Integr. | Registro + resultado con `modo: "reglas"` |
| **+ D-17** | Error | Vector mal formado al endpoint (longitud, rango, eje) | Rechazo con código de UT-02; no llega al motor | Unit | Resultado |
| **+ unidad** | Error (documental) | El `.jdx` real de estireno con `##YUNITS=dispersion index` | **Hoy pasa la validación y llega al motor.** La prueba deja constancia del comportamiento actual; el comportamiento deseado depende de la decisión abierta de `##YUNITS=` (sección 12) | Unit (MOD-03) | Resultado + archivo |
| **+ UT-03** | Error | `wR + wML ≠ 1` en la configuración | Error de configuración claro; no arranca en silencio | Unit (UT-03) | Registro |

**Disciplina de pruebas:** todas corren **sin red**. Las pruebas que tocan el modelo usan un archivo de pesos de prueba o se marcan como omitidas con su razón — nunca descargan ni entrenan dentro de la suite. Y se aplica la prueba de mutación: romper el umbral, el orden y una regla de desempate a propósito, y confirmar que una prueba revienta en cada caso.

---

## 10. Datos y persistencia de este incremento

Alineado con la decisión de persistencia v2: **sin base de datos**, archivos de solo lectura a través de UT-01.

| Qué | Dónde | Quién lo lee | ¿Al repositorio? |
|---|---|---|---|
| Catálogo de los 7 grupos | `datos/catalogo/grupos.json` | UT-01 → MOD-06 (y MOD-07, MOD-08) | **Sí** |
| Modelo entrenado (pesos) | `motor_identificacion/modelo/` | UT-01, al arrancar | Según D-18: fuera durante la iteración, uno final para la entrega |
| Índice del dataset y split de prueba | `datos/dataset/indice.csv`, `split-prueba.txt` | el script de entrenamiento | **Sí** (hace auditable RNF-08) |
| Los espectros del dataset | fuera del repositorio | el script de entrenamiento | **No** (licencia y tamaño) |
| Espectros de referencia de las pruebas | `datos/referencia/` | las pruebas | **Sí**, con su nota de origen y términos revisados |
| Vector, confianzas y resultado de un análisis | memoria, durante la petición | MOD-06, MOD-01 | **No** — nada se persiste (RNF-09) |

**Riesgos de datos propios de este incremento:** que el catálogo falte o se corrompa (se valida al cargar, como UT-03 en el incremento 1); que el modelo falte (D-16.4, degrada a reglas); que el split de prueba se contamine al reentrenar (lo previene congelarlo y versionar su suma de verificación).

---

## 11. Riesgos

Los del Plan V3 Paso 8 para este incremento, más los que aparecen al detallarlo.

| Riesgo | Impacto | Acción preventiva |
|---|---|---|
| Disponibilidad y **licencia** del conjunto de espectros (riesgo abierto n.º 4) | Alto | Revisar los términos de NIST y SDBS **antes** de bajar en volumen; no versionar los espectros, solo el índice y el split |
| El motor no alcanza F1 ≥ 0.80 (RNF-08) | Alto | D-13 define la puerta con antelación; D-16 define el disparador del plan B; se documentan los grupos que queden bajo la meta con su support |
| **Mezcla de fases** en el dataset (gas vs condensada) | Alto | D-12: una sola fase, condensada; la fase se anota por archivo; los de fase gas se excluyen o se evalúan aparte |
| **Desbalance de clases** (C≡N raro, C=O en todo) | Alto | T-16a cuenta el support por clase antes de entrenar; T-16c lo atiende explícitamente; T-16d lo reporta junto al F1 |
| Traslape O–H/N–H y C=C/aromático (riesgo abierto n.º 6) | Medio | Reglas R-1 y R-2, con la banda acompañante como desempate; pruebas de regresión R-3 y R-4 |
| **El C=O de amida (1630–1700) cae parcialmente fuera de GF-05 (1670–1780)** | Bajo | Limitación conocida, documentada en la sección 4. R-2 evita que se reporte como C=C, así que es omisión y no falso positivo. Se revisa en T-20 con criterio químico; **no se ensancha GF-05 sin aprobación**, porque es §6.2 |
| **Deriva entre el preprocesamiento de entrenamiento y el de producción** (MOD-06 §11) | Alto | T-16b: el entrenamiento importa la normalización real de MOD-04, y una prueba lo demuestra |
| **Cruce del orden de etiquetas** entre T-14 y T-16 | Alto | El orden canónico queda fijado en la sección 4 de este plan, una sola vez |
| Pesos de la fusión mal calibrados (una vía domina a la otra) | Medio | Arrancar en 0.5/0.5; recalibrar **solo** con el split de validación (D-15) |
| **RNF-02** se rompe al entrar el modelo | Medio | El modelo se carga una vez al arrancar (MOD-06 §9); se mide el tiempo en H10, no se estima |
| **Sobrecarga en T-16**, que está en la ruta crítica | Alto | Una persona dedicada a T-16 desde el día uno; la otra avanza T-14, T-15, T-18, T-19 |
| El binario del modelo infla el repositorio | Bajo | D-18: fuera durante la iteración; uno final para la entrega, o Git LFS |
| T-3R se delega al agente de código y trae archivos inservibles | Medio | Es trabajo humano: elegir fase, rango y puntos es una decisión química |

---

## 12. Decisiones abiertas y herencia

**Que este incremento hereda sin resolver (vienen de antes):**

- `SUPUESTO` — **validar `##YUNITS=`**: en cuatro descargas reales del incremento 1 aparecieron tres unidades distintas (transmitancia, reflectancia, índice de refracción), y §6.1 solo admite transmitancia y absorbancia, pero ningún CA lo cubre. Es un **cambio de alcance** que requiere aprobación. Si se cerró en el incremento 2, anotarlo aquí y tacharlo.
  - **Ya dejó de ser hipotético (23/11/2026).** El `.jdx` de estireno descargado trae `##YUNITS=dispersion index` y **pasaría la validación actual**: llegaría a MOD-04 y el motor produciría gráfica y detecciones a partir de números que no son intensidades. Es un resultado silenciosamente incorrecto, que es la peor clase de error. El archivo queda en `datos/referencia/` como caso de error real y como argumento para cerrar la decisión: añadir la lista de unidades admitidas a UT-03, la verificación a MOD-03 y su mensaje a UT-02. **Sigue requiriendo aprobación del equipo: no se implementa por cuenta propia dentro del incremento 3.**
- Pendiente documental: las menciones de `.dx` que quedan en el PDF de Requerimientos (RF-01 sobre todo). No afecta código; deja limpia la trazabilidad de la entrega.

**Que este incremento genera y hay que escribir fuera de él:**

- **La actualización de RNF-08** en Requerimientos §8 y §11.2, con fila nueva en Control de versiones (V3.3), y la redacción literal en MOD-06 §8 (v2.1) — ver la tabla de D-13.
- **La limitación de fase condensada** (de D-12), en **dos** sitios de Requerimientos V3.3:
  - **§6.1, «Parámetros de entrada y de análisis»** — es su sitio natural, porque esa tabla ya contiene «Unidades de intensidad». Fila nueva: *Fase de la muestra · Condensada (líquido o sólido) · Los espectros de referencia y el ajuste del motor usan fase condensada; en fase gas la banda ancha de O–H desaparece y las posiciones de banda se corren.*
  - **§5, «Fuera del alcance»** — fila nueva: *Espectros de fase gas · Quedan fuera del régimen para el que se ajustó el motor; se declara como limitación conocida.*
  - **Y una advertencia para quien implemente:** esto **no es una validación**. MOD-03 no puede deducir la fase del archivo, así que no hay CA ni regla que lo verifique. Es una limitación **declarada**, no comprobada. Que nadie intente hacer que MOD-03 la valide.

**Para el manual de usuario (RNF-07), cuando se escriba.** Todavía no existe; queda aquí la lista de lo que tendrá que decir, para no reconstruirla después:

- La herramienta trabaja con espectros de **fase condensada**; con fase gas el resultado no es confiable, sobre todo en O–H.
- Reconoce **siete grupos funcionales** y **no identifica la molécula completa** ni cuantifica.
- Qué significa el **nivel de confianza** y por qué solo se listan los que alcanzan el **60 %**.
- Qué pasa cuando **no hay detecciones confiables**: es un resultado honesto, no un fallo.
- Formatos admitidos (.jdx, .csv), tamaño máximo (5 MB), mínimo de puntos (300) y rango requerido (1400–3700 cm⁻¹).
- El resultado es **orientativo** (ya exigido por RF-08 para el reporte).
- Si el motor corrió en **modo reglas** (plan B de D-16), decirlo.
- Los grupos que hayan quedado por debajo de la meta de F1, con su cifra: lo que RNF-08 obliga a documentar y no ocultar.

**Que este incremento deja al incremento 4:**

- **T-20 (plantillas de explicación) es adelantable**: solo depende de T-14.
- MOD-07 y MOD-08 deben tratar **`evidencia.ml` como anulable** y leer `modo` (D-16.3). Cuesta cero hoy.
- Si el motor entregó en **modo reglas**, el reporte del incremento 5 debería decirlo, junto al aviso de resultado orientativo que ya exige RF-08.
- `pico_cm1` puede venir `null`: es el caso CA-06.3, y MOD-05 debe resaltar la región completa.
- Los **subtipos de C=O** del catálogo quedan listos para las explicaciones, sin haber sido detecciones separadas.
- Los grupos que hayan quedado por debajo de la meta de F1 se documentan con su support: la capa educativa debería ser más prudente al explicarlos.

---

## 13. Fuentes externas usadas en este plan

- NIST Chemistry WebBook (`webbook.nist.gov`) — identificadores de especie verificados: benzonitrilo `C100470` (100-47-0), ciclohexeno `C110838` (110-83-8), estireno `C100425` (100-42-5), tolueno `C108883` (108-88-3), **ciclohexano `C110827` (110-82-7 — compuesto distinto del ciclohexeno)**, fenol `C108952` (108-95-2), acetonitrilo `C75058` (75-05-8), 1-hexeno `C592416` (592-41-6), acetato de etilo `C141786` (141-78-6), ciclohexanol `C108930`, acetato de butilo `C123864`. La fase del espectro **no** aparece en la página de especie: hay que verla al abrir el espectro, donde además se elige entre varias entradas (líquido neto, disolución, gas). Las páginas llevan la nota de *data compilation copyright* del U.S. Secretary of Commerce.
- Los rangos de los 7 grupos provienen de Requerimientos V3.2 §6.2 y de MOD-06 §4, que a su vez citan la tabla de absorciones IR de la University of Colorado Boulder y LibreTexts.
- **Conjunto de entrenamiento (D-12, opción B):** Jung, N.; Tremouilhac, P.; Punjabi, D.; Huang, P.-C. (2024). *Chemotion repository — data collection: ft-ir spectroscopy data (chemotion ir)*. Karlsruhe Institute of Technology. DOI `10.22000/OGoEQGlsZGElrgst`. Licencia **CC BY-SA 4.0**. 4 183 espectros `.jdx` con `cano_smiles` en el metadato.
- **Referencia metodológica:** Punjabi, D. *et al.* (2025). «Infrared spectrum analysis of organic molecules with neural networks using standard reference data sets in combination with real-world data». *Journal of Cheminformatics* 17:24. Acceso abierto CC BY 4.0. F1 > 0.7 para 17 grupos funcionales con NIST SRD 35 + Chemotion.

---

## 14. Registro de lo implementado

*(Esta sección se llena al cerrar el incremento, siguiendo la convención de `incremento-2.md` §11: cómo quedaron en el código las decisiones de arriba, qué se resolvió por el camino y qué quedó marcado `SUPUESTO` para que el equipo lo confirme.)*

- **D-12 / T-3R — conjunto de datos:** T-16a-2 está en `herramientas/dataset/etiquetar.py`. De los 2 113 análisis que pasan el embudo se toma un archivo por análisis, el original antes que el derivado, y se preparan por la ruta de producción de T-16b. Quedan 2 078 espectros distintos: 19 se quitan por repetidos del mismo compuesto y 16 porque el mismo espectro aparece con dos InChIKey distintos. Se excluyen 142 compuestos con metales u otros elementos fuera de la química orgánica y 3 sin InChIKey. Quedan 1 933 espectros de 1 771 compuestos, partidos por InChIKey en 1 356 de entrenamiento, 292 de validación y 285 de prueba, con semilla fija. Las etiquetas están en `datos/dataset/conjunto.csv`; cada celda vale 1, 0 o x (enmascarada). La lista de prueba está congelada en `datos/dataset/split-prueba.txt`. **PROVISIONAL:** el criterio es D-24 v2 del traspaso, sin firmar. Los dos casos marginales (imina en GF-06 y alquino terminal en GF-02) y los heteroaromáticos en GF-07 se enmascaran en lugar de adivinar.
- **D-13 / T-16d — métricas de RNF-08:** Las tablas están en `docs/evidencia/rnf-08.md`, de una sola corrida sobre prueba. La red sola tiene macro F1 de 0.857; el motor completo, 0.767; las reglas solas, 0.549. Puerta: GF-05 pasa, GF-01 no pasa (0.747 con la red sola) y GF-04 queda sin decidir porque solo hay 14 positivos en prueba. El mínimo de 20 positivos para decidir es **PROVISIONAL** (sección 4.4 del traspaso).
- **D-14 / T-3R — espectros de referencia añadidos:**
- **D-15 / T-17 — umbral y pesos:** UT-03 ya traía `umbral_confianza`, `peso_reglas` y `peso_ml` en el bloque `motor`; ahora el cargador los revisa. Cada peso va de 0 a 1, los dos suman 1 y el umbral es una fracción. Si no cuadra, el backend no arranca. La fusión vive en `motor_identificacion/inferencia/fusion.py` y compara el porcentaje entero, redondeando la mitad hacia arriba, contra el umbral en porcentaje. Las pruebas están en `backend/pruebas/prueba_t17_fusion.py`.
- **D-16 — ¿se activó el plan B?:** No. Nadie lo ha decidido y no se decide aquí. Desde T-16c la aplicación arranca en modo híbrido con la red del repositorio. GF-01 no pasa la puerta: eso es lo que el equipo tiene que revisar en H9. Antes de T-16c pasaba D-16.4: como no existe un modelo entrenado, la aplicación arranca en modo reglas, lo anota en el registro y la respuesta dice `"modo": "reglas"` con `evidencia.ml` en null. El hueco del modelo es el protocolo `ModeloML` de la fusión: T-16c solo tiene que entregar un objeto con `puntos_rejilla` y `probabilidades(ventana)` y pasarlo a `crear_aplicacion(modelo=...)`.
- **D-17 / T-18 — contrato de `/api/analizar`:** Recibe en JSON el objeto `espectro` de `/api/procesar` (también acepta la respuesta entera). Antes del motor se revisa la longitud, el eje contra la rejilla de UT-03, los valores entre 0 y 1 y el tramo medido; si algo falla responde 200 con `ESPECTRO_INVALIDO`. Si todo sale bien responde 200 con `{valido, detecciones, sin_detecciones, umbral, modo}`; cada detección lleva además `nombre`, de UT-01, y `porcentaje`, el número con que se decidió. Sin detecciones agrega `aviso` con el texto de UT-02 (`SIN_DETECCIONES`). Un fallo del motor responde 500 con `ANALISIS_FALLIDO`. Este código es nuevo y se aparta de lo que decía D-17: `FALLO_INTERNO` dice «No se pudo revisar el archivo» y CA-05.4 pide literalmente «No fue posible completar el análisis; intenta de nuevo».
- **D-18 — dónde quedó el modelo:** La red se entrena con PyTorch (`herramientas/entrenamiento/entrenar.py`, semilla 20261124) y se guarda en `motor_identificacion/modelo/red.npz`, de unos 800 KB, con su descripción y la N de la rejilla adentro. La aplicación la corre con NumPy (`motor_identificacion/inferencia/red.py`), así que PyTorch no es dependencia del backend. `crear_aplicacion()` la carga por omisión; si falta o no cuadra, sigue en modo reglas. Se versiona este archivo, con su nota de licencia en `motor_identificacion/modelo/LEEME.md`, para que la aplicación funcione al clonar.
- **D-19 — N y la comprobación de arranque:** `motivo_para_solo_reglas` compara `puntos_rejilla` del modelo con UT-03. Si no coinciden el modelo no se usa y la aplicación sigue en modo reglas. Hay prueba con un modelo de mentira de otra rejilla.
- **Reglas de desempate R-1 a R-4 — cómo quedaron:**
- **Evidencia:** `docs/evidencia/t-18-lista-carbonilo.png`, la página real con un CSV fabricado con un carbonilo en 1715 (C=O al 80 %). T-16b, la paridad entre entrenamiento y producción, está en `backend/pruebas/prueba_t16b_paridad.py` y `herramientas/entrenamiento/preparar.py`; una mutación que quita el redondeo de seis decimales la hace fallar.
- **Pendientes:**
  - **CA-08.1 y CA-08.3 no se cumplen con la vía de reglas actual.** Sobre ruido puro reporta entre cinco y seis grupos (62 a 80 %), y sobre una línea base inclinada o curva reporta O–H al 100 % sin pico. Las pruebas quedan como fallo esperado estricto en `prueba_t18_t19_analizar.py`. Coincide con la hipótesis del traspaso: los pisos de D-22 son el punto débil. No se movió ningún piso ni umbral; se quita la marca cuando el motor acierte.
  - CA-05.1 y CA-05.2 tienen su prueba con los espectros reales, pero se saltan donde falta `datos/referencia`. Hay que correrlas en una computadora del equipo.
  - T-16a-2, T-16c y T-16d se hicieron el 24/11/2026 con el visto bueno del equipo para entrenar, pero con D-24 v2 y las secciones 4.2 a 4.4 del traspaso todavía sin firmar. Falta que el equipo las firme o pida cambios.
  - Con la red, CA-08.3 ya se cumple con la línea base curva; con la inclinada y con el ruido de CA-08.1 el motor completo todavía reporta grupos.
  - Sin hacer: T-15e (CA-06.2, toca R-1) y la recalibración de los pesos de la fusión con el conjunto de validación (D-15).
