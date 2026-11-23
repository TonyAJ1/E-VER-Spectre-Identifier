"""Orquestación HTTP (T-07) · MOD-01 → api → MOD-02 → MOD-03.

Es el único punto de entrada del servidor:

    uvicorn backend.api.aplicacion:app --port 8000

y después se abre http://localhost:8000/ en el navegador.

**Contrato D-5** (sección 5 del plan del incremento 1):

- `POST /api/validar`, `multipart/form-data`, campo `archivo`.
- **200** siempre que haya veredicto, porque un rechazo es un resultado de
  negocio y no un error de transporte:
  - aceptado → ``{"valido": true, "nombre": "...", "bytes": 307200}``
  - rechazado → ``{"valido": false, "codigo", "titulo", "mensaje", "accion"}``
- **500** solo ante un fallo interno, con el mensaje genérico de UT-02 y sin
  detalles técnicos.

Lo que este módulo **no** hace, a propósito:

- No aplica el tamaño máximo ni revisa el contenido: eso lo hacen MOD-02 y
  MOD-03. Si el límite lo cortara el servidor, CA-02.2 no probaría el código
  del equipo.
- No escribe textos: todo mensaje sale de UT-02.
- No guarda nada (RNF-09): el archivo vive en memoria durante la petición y la
  subida se cierra siempre, con éxito o con error.

**Arranque:** la configuración de UT-03 se carga al crear la aplicación. Si le
falta una llave obligatoria, el servidor **no arranca** y dice cuál (prueba
«UT-03 · configuración incompleta» de T-01).

**La página (MOD-01)** la sirve este mismo servidor, desde `frontend/`. Así la
interfaz llama a `/api/validar` en su propio origen, sin abrir CORS.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile

from backend.manejador_archivos import recibir
from backend.nucleo import NOMBRE_RAIZ, obtener_registro
from backend.api import analisis, reporte
from backend.preprocesamiento.procesador import EspectroProcesado, procesar
from backend.utilerias.catalogo import Catalogo
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion
from backend.utilerias.configuracion import obtener as obtener_configuracion
from backend.validacion import validar

_registro = obtener_registro("api")

#: Ruta del contrato D-5.
RUTA_VALIDAR: str = "/api/validar"

#: Nombre del campo del formulario (contrato D-5).
CAMPO_ARCHIVO: str = "archivo"

#: Carpeta del frontend que sirve este servidor, y la página de inicio.
CARPETA_FRONTEND: Path = Path(__file__).resolve().parents[2] / "frontend"
PAGINA_INICIO: str = "/interfaz/"


def configurar_registro(nivel: int = logging.INFO) -> None:
    """Manda los registros del proyecto a la consola, una sola vez.

    `backend/nucleo/registro.py` deja esta decisión al arranque. Los registros
    guardan nombre, tamaño y resultado; nunca el contenido (RNF-09).
    """
    raiz = logging.getLogger(NOMBRE_RAIZ)
    raiz.setLevel(nivel)
    if not any(getattr(h, "_e_ver", False) for h in raiz.handlers):
        consola = logging.StreamHandler()
        consola.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s · %(message)s")
        )
        consola._e_ver = True  # type: ignore[attr-defined]
        raiz.addHandler(consola)


def crear_aplicacion(
    configuracion: Configuracion | None = None, catalogo: Catalogo | None = None
) -> FastAPI:
    """Arma la aplicación.

    Args:
        configuracion: los parámetros con los que trabaja. Si es ``None`` se
            cargan de UT-03 **ahora**, de modo que un archivo incompleto impide
            arrancar. El parámetro existe para las pruebas.

    Raises:
        ErrorDeConfiguracion: si UT-03 está incompleta o es incoherente.
    """
    parametros = configuracion if configuracion is not None else obtener_configuracion()
    # El catálogo de UT-01 también se carga al arrancar: sin él MOD-06 no
    # puede trabajar, y es mejor que el servidor no levante a que falle en
    # medio de un análisis.
    grupos = catalogo if catalogo is not None else obtener_catalogo()
    configurar_registro()

    aplicacion = FastAPI(
        title="E-VER Spectre Identifier",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @aplicacion.post(RUTA_VALIDAR)
    async def validar_espectro(peticion: Request) -> JSONResponse:
        formulario = None
        try:
            formulario = await peticion.form()
            archivo = formulario.get(CAMPO_ARCHIVO)
            if not isinstance(archivo, UploadFile):
                return _rechazo(mensajes.ARCHIVO_NO_RECIBIDO, parametros)
            return await _validar(archivo, parametros)
        except Exception as error:
            # Ni el tipo ni el texto de la excepción llegan al usuario ni al
            # registro: pueden traer rutas de temporales o contenido.
            _registro.error(
                "api fallo interno | ruta=%s | tipo=%s",
                RUTA_VALIDAR,
                type(error).__name__,
            )
            return _respuesta_de(mensajes.ERROR_INTERNO, parametros, estado=500)
        finally:
            # Cierra todo lo que se subió en el formulario (MOD-02 ya cerró el
            # archivo; esto alcanza también campos de más). RNF-09.
            if formulario is not None:
                await formulario.close()

    # Incremento 3: la ruta del análisis vive en backend/api/analisis.py.
    analisis.registrar(aplicacion, parametros, grupos)
    # Incremento 5: la ruta del reporte PDF vive en backend/api/reporte.py.
    reporte.registrar(aplicacion, parametros, grupos)

    @aplicacion.get("/", include_in_schema=False)
    async def inicio() -> RedirectResponse:
        return RedirectResponse(PAGINA_INICIO)

    aplicacion.mount(
        "/", StaticFiles(directory=CARPETA_FRONTEND, html=True), name="frontend"
    )

    return aplicacion


async def _validar(archivo: UploadFile, parametros: Configuracion) -> JSONResponse:
    """MOD-02 y después MOD-03, en ese orden y sin atajos."""
    recepcion = await recibir(archivo, parametros)
    if not recepcion.aceptado:
        return _rechazo(recepcion.codigo, parametros)

    veredicto = validar(
        recepcion.nombre,
        recepcion.contenido,
        tamano_correcto=recepcion.tamano_correcto,
        configuracion=parametros,
    )
    if not veredicto.valido:
        return _rechazo(veredicto.codigo, parametros)

    # Incremento 2: el archivo aprobado pasa por MOD-04 en la misma petición,
    # porque no se guarda en ningún lado (RNF-09). Si sus datos no se pueden
    # leer o es una línea plana, es un rechazo más con su mensaje de UT-02.
    resultado = procesar(recepcion.nombre, recepcion.contenido, parametros)
    if not resultado.valido:
        return _rechazo(resultado.codigo, parametros)

    return JSONResponse(
        {
            "valido": True,
            "nombre": recepcion.nombre,
            "bytes": recepcion.bytes_leidos,
            "espectro": _espectro_como_json(resultado.espectro),
        }
    )


#: Decimales con que viajan el eje y la intensidad. Seis alcanzan de sobra
#: para la gráfica y dejan la respuesta en unas pocas decenas de kilobytes.
_DECIMALES = 6


def _espectro_como_json(espectro: EspectroProcesado) -> dict[str, Any]:
    return {
        "eje_cm1": [round(valor, _DECIMALES) for valor in espectro.eje_cm1],
        "intensidad": [round(valor, _DECIMALES) for valor in espectro.intensidad],
        "rango_medido_cm1": list(espectro.rango_medido_cm1),
        "unidad_original": espectro.unidad_original,
    }


def _rechazo(codigo: str, parametros: Configuracion) -> JSONResponse:
    return _respuesta_de(codigo, parametros, estado=200, valido=False)


def _respuesta_de(
    codigo: str,
    parametros: Configuracion,
    *,
    estado: int,
    valido: bool | None = None,
) -> JSONResponse:
    """El cuerpo del contrato D-5 con el mensaje de UT-02."""
    mensaje = mensajes.obtener(codigo, parametros)
    cuerpo: dict[str, Any] = {}
    if valido is not None:
        cuerpo["valido"] = valido
    cuerpo.update(
        codigo=mensaje.codigo,
        titulo=mensaje.titulo,
        mensaje=mensaje.texto,
        accion=mensaje.accion,
    )
    return JSONResponse(cuerpo, status_code=estado)


#: La aplicación que levanta uvicorn. Crearla aquí carga UT-03 al arrancar.
app = crear_aplicacion()
