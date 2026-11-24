# La red de la vía ML (T-16c)

`red.npz` guarda los pesos de la CNN 1D y, dentro del mismo archivo, su
descripción: la N de la rejilla con que se entrenó (D-19), el orden de los
grupos, el largo de la ventana, la semilla, la época elegida y la suma de
verificación del conjunto de prueba.

La aplicación la lee con NumPy desde `motor_identificacion/inferencia/red.py`.
Si el archivo falta o no corresponde a la configuración, la aplicación sigue
solo con reglas (D-16).

Para volver a entrenarla:

```bash
python -m herramientas.dataset.descargar_chemotion   # o el .tar ya descargado
python -m herramientas.dataset.embudo_chemotion
python -m herramientas.dataset.etiquetar
python -m herramientas.entrenamiento.entrenar
```

## Licencia de origen

Los pesos se entrenaron con el conjunto Chemotion IR:

> Jung, Nicole; Tremouilhac, Pierre; Punjabi, Dev; Huang, Pei-Chi (2024).
> *Chemotion repository — data collection: ft-ir spectroscopy data (chemotion ir)*.
> Karlsruhe Institute of Technology. DOI 10.22000/OGoEQGlsZGElrgst

Ese conjunto se publica con licencia CC BY-SA 4.0. SUPUESTO: que unos pesos
entrenados con él se puedan versionar con esta atribución; es la verificación
4 de D-12 y la tiene que confirmar el equipo o un profesor.
