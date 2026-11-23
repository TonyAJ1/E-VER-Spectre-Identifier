# CLAUDE.md — E-VER Spectre Identifier

Instrucciones permanentes para Claude Code en este repositorio. Léelas antes de cada tarea.

## Qué es el proyecto
Aplicación web que recibe un espectro infrarrojo (IR) en `.jdx` o `.csv`, lo valida, lo normaliza,
identifica 7 grupos funcionales con un motor híbrido (reglas + CNN 1D), resalta los picos con una
explicación educativa y genera un reporte PDF.

- Materia: Desarrollo de Aplicaciones y Servicios Virtuales · Universidad Iberoamericana León
- Equipo E-VER: Sergio Uriel Bustamante Bustos, Julio Antonio Jiménez Jiménez
- El equipo **no programa a mano**: explica siempre en español claro qué vas a hacer y por qué,
  antes de escribir código.

## Documentos fuente de verdad (en `docs/`)
1. Requerimientos **V3** (RF-01…09, RNF-01…09, HU, CA-01.1…CA-09.3, incluye CA-02.6)
2. Diseño modular **v2** (MOD-01…08, UT-01…03, carpetas)
3. Diseño detallado de MOD-06 **v2** (motor, contrato de datos §5, plan B §10)
4. Persistencia **v2** (sin base de datos)
5. Plan de Implementación **V2** (tareas T-01…T-27, pruebas, hitos, riesgos)

Resumen operativo del incremento actual: `docs/plan/incremento-1.md`.
Si algo en el código contradice estos documentos, **detente y pregunta**; no lo resuelvas por tu cuenta.

## Stack (confirmado)
- Backend: **Python + FastAPI**
- Frontend: **HTML/CSS/JS puro** (sin framework)
- Sin base de datos: archivos de solo lectura (catálogo JSON y pesos del modelo)
- Pruebas: pytest (recomendado; el equipo lo confirma en T-01)

## Módulos y carpetas
| ID | Módulo | Carpeta |
|---|---|---|
| MOD-01 | Interfaz web | `frontend/interfaz/` |
| MOD-02 | Manejador de archivos | `backend/manejador_archivos/` |
| MOD-03 | Validador | `backend/validacion/` |
| MOD-04 | Procesador de espectros | `backend/preprocesamiento/` |
| MOD-05 | Visualizador de espectro | `frontend/visor-espectro/` |
| MOD-06 | Motor de identificación (aislado) | `motor_identificacion/` |
| MOD-07 | Capa educativa | `backend/educativo/` |
| MOD-08 | Generador de reportes | `backend/reportes/` |
| UT-01 | Catálogo de grupos funcionales | `backend/utilerias/catalogo/` + `datos/catalogo/` |
| UT-02 | Errores y mensajes | `backend/utilerias/mensajes/` |
| UT-03 | Configuración | `backend/utilerias/configuracion/` |

Orquestación HTTP: `backend/api/`. Infraestructura base (arranque, logging): `backend/nucleo/`.
Pruebas del backend: `backend/pruebas/`, **solo código** (RNF-06). Los **datos** de prueba viven en
`datos/pruebas/` (fixtures fabricados, versionados) y `datos/referencia/` (espectros reales, fuera
del repositorio); los pesados los genera `backend/pruebas/conftest.py` al arrancar las pruebas y
nunca se commitean (D-8).

**Nombres de carpeta (D-7):** las carpetas que Python importa como paquete usan **guion bajo**,
porque un guion no es identificador válido y `import` sobre ellas es error de sintaxis. Por eso
`backend/manejador_archivos/` y `motor_identificacion/` (renombrada en el incremento 3).
Las carpetas del frontend (`interfaz/`, `servicios/`, `visor-espectro/`) conservan el guion.

## Reglas que no se rompen
1. **Parámetros solo desde UT-03.** Nunca escribas en el código 5 MB, 300 puntos, 1400–3700 cm⁻¹,
   formatos, umbral 60 % ni pesos de la fusión: léelos de la configuración.
2. **Mensajes solo desde UT-02.** El usuario nunca ve errores técnicos; cada rechazo trae motivo y acción.
3. **Privacidad (RNF-09):** el archivo se procesa **en memoria**, nunca se escribe en disco, el archivo
   subido se cierra siempre (try/finally) y los logs no guardan el contenido del espectro.
4. **Seguridad (RNF-03):** el archivo se lee como texto, jamás se ejecuta; no confíes en la extensión
   ni en el tamaño que declara el navegador (lee por bloques y corta al pasar el límite).
5. **MOD-06 está aislado:** solo recibe el vector numérico normalizado + eje; nunca el archivo.
6. **No cambies la arquitectura** (módulos, contratos, carpetas) sin explicar la razón y pedir aprobación.
7. **No agregues funciones fuera del alcance** del incremento en curso.
8. **No inventes datos.** Si falta algo, márcalo como SUPUESTO y pregunta.

## Forma de trabajar (una tarea a la vez)
1. Lee la tarea en `docs/plan/` y explica el enfoque en español antes de escribir código.
2. Escribe primero las pruebas de esa tarea (los CA indicados en el plan).
3. Implementa lo mínimo para que pasen.
4. Ejecuta todas las pruebas y muestra el resultado real; no afirmes que algo funciona sin correrlo.
5. Propón el commit con el ID de la tarea, p. ej. `T-01: parámetros centralizados en UT-03`.
6. Resume qué hiciste y qué debe registrar el equipo en la bitácora de IA.

## Decisiones técnicas pendientes (no las tomes solo; pregunta al llegar)
- D-1 · Librería de gráficas de MOD-05 (incremento 2, antes de T-12)
- D-2 · «Lector de espectro» compartido MOD-03/MOD-04 (incremento 2, antes de T-08)
- D-3 · Librería de PDF de MOD-08 (incremento 5, antes de T-25)
