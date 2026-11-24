"""T-16b: el vector con que se entrena es el mismo que ve la aplicación.

El riesgo que esto evita está en el diseño de MOD-06 (sección 11): si el
entrenamiento normaliza distinto que producción, el modelo acierta en el
cuaderno y falla en la aplicación, y el síntoma aparece lejísimos de la causa.

Por eso aquí no hay ni una cuenta propia. Un espectro de entrenamiento recorre
exactamente lo mismo que uno que sube un usuario:

1. MOD-03 lo valida, con los parámetros de UT-03.
2. MOD-04 lo convierte, quita la línea base y lo normaliza.
3. Se redondea con los mismos decimales con que /api/procesar se lo manda a
   la página. Es lo que de verdad le llega al motor, porque la página reenvía
   ese mismo objeto a /api/analizar.
4. Se recorta la ventana que ve el modelo con la misma función que usa la
   fusión (T-17), así que los ceros de relleno tampoco entran al entrenar.

La prueba de paridad está en backend/pruebas/prueba_t16b_paridad.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.api.veredicto import DECIMALES_ESPECTRO
from backend.preprocesamiento import procesar
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion
from backend.validacion import validar
from motor_identificacion.inferencia import ventana_del_modelo


@dataclass(frozen=True)
class EspectroRedondeado:
    """El espectro tal como viaja por la aplicación, ya redondeado."""

    eje_cm1: tuple[float, ...]
    intensidad: tuple[float, ...]
    rango_medido_cm1: tuple[float, float]


@dataclass(frozen=True)
class Preparado:
    """Lo que sale de preparar un archivo para entrenar.

    Si el archivo no pasa, vector es None y codigo dice por qué, con el mismo
    código de UT-02 que vería un usuario.
    """

    vector: tuple[float, ...] | None
    codigo: str | None


def espectro_redondeado(
    nombre: str, contenido: str, configuracion: Configuracion | None = None
) -> tuple[EspectroRedondeado | None, str | None]:
    """El espectro completo tal como lo recibe el motor, o None y el código.

    La evaluación de T-16d lo usa para correr el motor completo, con las dos
    vías, sobre los mismos datos que vio el entrenamiento.
    """
    parametros = configuracion if configuracion is not None else obtener_configuracion()

    veredicto = validar(nombre, contenido, tamano_correcto=True, configuracion=parametros)
    if not veredicto.valido:
        return None, veredicto.codigo

    salida = procesar(nombre, contenido, parametros)
    if not salida.valido:
        return None, salida.codigo

    espectro = salida.espectro
    return (
        EspectroRedondeado(
            eje_cm1=tuple(round(x, DECIMALES_ESPECTRO) for x in espectro.eje_cm1),
            intensidad=tuple(round(y, DECIMALES_ESPECTRO) for y in espectro.intensidad),
            rango_medido_cm1=tuple(espectro.rango_medido_cm1),  # type: ignore[arg-type]
        ),
        None,
    )


def preparar(
    nombre: str, contenido: str, configuracion: Configuracion | None = None
) -> Preparado:
    """El vector de entrenamiento de un archivo, por la ruta de producción."""
    parametros = configuracion if configuracion is not None else obtener_configuracion()
    redondeado, codigo = espectro_redondeado(nombre, contenido, parametros)
    if redondeado is None:
        return Preparado(None, codigo)
    return Preparado(ventana_del_modelo(redondeado, parametros), None)
