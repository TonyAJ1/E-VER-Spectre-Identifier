"""Capa HTTP · `POST /api/validar` y el servicio del frontend (T-07).

Es un **orquestador delgado**: no valida nada por su cuenta. Encadena lo que ya
está probado aislado y traduce el resultado al contrato de la sección 5:

    archivo subido → MOD-02 (tamaño, leer como texto) → MOD-03 (formato,
    puntos, rango) → veredicto

Las cinco reglas que este archivo existe para sostener:

1. **La traducción vive en un solo lugar.** MOD-02 y MOD-03 devuelven códigos;
   `veredicto.py` les pone el texto de UT-02. Aquí no se redacta nada.
2. **200 mientras haya veredicto.** Que un espectro se rechace es un resultado
   del negocio, no un error de transporte. El 500 queda para lo que falla por
   dentro, con el mensaje genérico de UT-02 y sin un solo detalle técnico.
3. **El límite lo aplica MOD-02**, leyendo por bloques el tamaño de UT-03. No
   se configura ningún límite en FastAPI ni en el servidor: si lo cortara la
   infraestructura, CA-02.2 dejaría de probar el código del equipo.
4. **Si UT-03 está incompleta, no arranca.** La configuración se lee **una vez**
   al crear la aplicación y se le pasa a MOD-02, MOD-03 y UT-02. Así el 500
   puede armar su mensaje sin volver a leer el archivo de parámetros, y nadie
   atiende peticiones con una configuración a medias (T-01).
5. **Mismo origen.** El frontend se sirve desde aquí, así que el `fetch` del
   navegador a `/api/validar` no cruza dominios y no hace falta CORS.

Para levantarlo en local, desde la raíz del repositorio:

    uvicorn backend.api:crear_aplicacion --factory --reload

y la interfaz queda en `http://127.0.0.1:8000/`.

**Privacidad (RNF-09):** el contenido del archivo existe solo durante la
petición y nunca se escribe en disco desde aquí; MOD-02 cierra la subida en un
`finally`, de modo que el temporal que FastAPI crea arriba de 1 MB desaparece
pase lo que pase. El registro guarda nombre, bytes y resultado; nunca el
espectro.
"""

from __future__ import annotations

import json
import mimetypes
import re
import unicodedata
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from backend.api.entrada_analisis import espectro_desde
from backend.api.entrada_reporte import peticion_desde
from backend.api.veredicto import aceptado, analizado, procesado, rechazado
from backend.manejador_archivos import recibir
from backend.nucleo import obtener_registro
from backend.preprocesamiento import procesar
from backend.reportes import DatosDelReporte, generar_pdf
from backend.utilerias import mensajes
from backend.utilerias.configuracion import Configuracion, ErrorDeConfiguracion
from backend.utilerias.configuracion import obtener as obtener_configuracion
from backend.educativo import explicar
from backend.utilerias.catalogo import obtener as obtener_catalogo
from backend.utilerias.catalogo import obtener_plantillas
from backend.validacion import validar
from motor_identificacion.inferencia import ModeloML, identificar, motivo_para_solo_reglas
from motor_identificacion.inferencia.red import ErrorDeModelo, cargar_red

_registro = obtener_registro("api")

#: La ruta y el campo del contrato D-5. `frontend/servicios/validacion.js`
#: repite estos dos valores porque no puede importar Python; una prueba falla si
#: se separan.
RUTA_VALIDAR: str = "/api/validar"

#: Incremento 2. Recibe el mismo archivo, lo pasa otra vez por MOD-02 y MOD-03
#: y después por MOD-04, y devuelve el espectro normalizado para la gráfica.
#: Es una ruta aparte para no cambiar el contrato D-5 de /api/validar, que el
#: incremento 1 dejó cerrado en {valido, nombre, bytes}. Como el archivo no se
#: guarda en ningún lado (RNF-09), la página lo vuelve a mandar.
#: `frontend/servicios/procesamiento.js` repite esta ruta.
RUTA_PROCESAR: str = "/api/procesar"
#: Incremento 3 (D-17). Recibe en JSON el objeto espectro que entregó
#: /api/procesar y responde la salida del motor. No recibe el archivo: el motor
#: solo ve números. `frontend/servicios/analisis.js` repite esta ruta.
RUTA_ANALIZAR: str = "/api/analizar"

#: Incremento 5. Recibe el espectro, el nombre y la gráfica resaltada como
#: PNG, y responde el PDF. `frontend/servicios/reporte.js` repite esta ruta.
RUTA_REPORTE: str = "/api/reporte"

#: Cuántas veces el tamaño máximo de UT-03 puede medir el cuerpo JSON de
#: /api/analizar y /api/reporte. La imagen en base64 crece un tercio y el
#: espectro ocupa unas decenas de kilobytes, así que dos veces sobra.
FACTOR_CUERPO_JSON: int = 2

CAMPO_ARCHIVO: str = "archivo"

#: Dónde se sirve cada carpeta del frontend. Se conservan los nombres del
#: repositorio para que las rutas relativas de la página funcionen sin tocar ni
#: una línea del frontend: `/interfaz/interfaz.js` importa
#: `../servicios/validacion.js` y da justo en `/servicios/validacion.js`.
RUTA_INTERFAZ: str = "/interfaz"
RUTA_SERVICIOS: str = "/servicios"
#: Incremento 2: la gráfica (MOD-05) y las librerías guardadas en el repositorio
#: (D-1). Se montan aparte, igual que las otras, para no publicar
#: `frontend/pruebas/`.
RUTA_VISOR: str = "/visor-espectro"
RUTA_LIBRERIAS: str = "/vendor"

#: La raíz del frontend. `frontend/pruebas/` (D-9) **no** se monta: es del
#: equipo, no de la web.
CARPETA_FRONTEND: Path = Path(__file__).resolve().parents[2] / "frontend"

#: Petición que no se puede atender: no llegó el archivo, así que no hay nada
#: que validar y tampoco falló nada por dentro.
CODIGO_PETICION_INVALIDA: int = 400

#: Fallo interno (sección 5).
CODIGO_FALLO_INTERNO: int = 500


def _preparar_tipos() -> None:
    """Asegura el tipo de los archivos del frontend.

    En Windows, `mimetypes` consulta el registro y `.js` puede quedar como
    `text/plain`. Con ese tipo, el navegador **se niega** a ejecutar un módulo
    (`<script type="module">`) y la página se queda muerta sin decir por qué. Es
    el tipo de detalle que solo aparece al servir de verdad.
    """
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/css", ".css")


def _configuracion_de_arranque() -> Configuracion:
    """Lee UT-03 al arrancar y, si está incompleta, falla ruidoso (T-01)."""
    try:
        return obtener_configuracion()
    except ErrorDeConfiguracion as error:
        # El código de UT-02 queda en el registro para que el equipo lo
        # reconozca; el detalle técnico se queda aquí y no viaja a ninguna
        # pantalla, porque con la configuración rota no hay servicio que dar.
        _registro.critical(
            "api arranque | resultado=%s | detalle=%s",
            mensajes.CONFIGURACION_INCOMPLETA,
            error,
        )
        raise


#: El valor por omisión de `modelo` en crear_aplicacion: cargar la red que
#: está guardada en el repositorio (T-16c). Las pruebas pasan None para
#: trabajar solo con reglas.
MODELO_DEL_REPOSITORIO = "red del repositorio"


def _modelo_de_arranque(catalogo: Any) -> ModeloML | None:
    """La red guardada en motor_identificacion/modelo, o None si no se puede.

    Que no haya red no es un error (D-16): se anota en el registro y la
    aplicación sigue solo con reglas.
    """
    try:
        return cargar_red(grupos_esperados=tuple(g.id for g in catalogo.grupos))
    except ErrorDeModelo as error:
        _registro.info("motor arranque | red no cargada | motivo=%s", error)
        return None


async def _leer_json(peticion: Request, limite_bytes: int) -> Any:
    """El JSON del cuerpo, o None si no es JSON o pasa del límite.

    Se lee por bloques y se corta al pasar el límite, igual que MOD-02 hace con
    los archivos (RNF-03): no se confía en el tamaño que declara el navegador.
    """
    recibido = bytearray()
    async for bloque in peticion.stream():
        recibido.extend(bloque)
        if len(recibido) > limite_bytes:
            return None
    try:
        return json.loads(recibido)
    except ValueError:
        return None


def _nombre_de_descarga(nombre: str) -> str:
    """El nombre del PDF descargado, solo con letras, números y guiones."""
    base = nombre.rsplit(".", 1)[0]
    simple = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    limpio = re.sub(r"[^A-Za-z0-9_-]+", "-", simple).strip("-")[:80]
    return f"reporte-{limpio or 'espectro'}.pdf"


def crear_aplicacion(
    configuracion: Configuracion | None = None,
    *,
    carpeta_frontend: Path | None = None,
    modelo: ModeloML | str | None = MODELO_DEL_REPOSITORIO,
) -> FastAPI:
    """Arma la aplicación.

    Args:
        configuracion: los parámetros con los que trabajará. Si es ``None`` se
            leen de UT-03 —y si falta algo, **no arranca**—. El parámetro existe
            para las pruebas y para la evidencia, que levantan la aplicación con
            una configuración distinta para comprobar que UT-03 manda de verdad.
        carpeta_frontend: de dónde servir la interfaz. Si es ``None``, la del
            repositorio. La herramienta de evidencia pasa una **copia temporal**
            con un archivo extra que dispara la subida sola para la captura; así
            el frontend del repositorio no lleva ganchos de prueba.
        modelo: la red neuronal de T-16. Por omisión se carga la que está
            guardada en motor_identificacion/modelo. Con None, o si esa red
            no existe o no corresponde a la configuración, el motor trabaja
            solo con reglas, como pide D-16. La aplicación lo anota en el
            registro al arrancar y no se lo muestra al usuario.

    Returns:
        La aplicación lista para servir.

    Raises:
        ErrorDeConfiguracion: si UT-03 está incompleta y no se pasó una
            configuración. Es a propósito: más vale no arrancar que arrancar
            mal (T-01).
    """
    parametros = (
        configuracion if configuracion is not None else _configuracion_de_arranque()
    )
    _preparar_tipos()

    # UT-01 se lee una vez al arrancar, igual que UT-03: si el catálogo está
    # roto, mejor no arrancar que fallar en el primer análisis.
    catalogo = obtener_catalogo()
    plantillas = obtener_plantillas()

    def explicar_detecciones(resultado: Any) -> dict[str, Any]:
        """MOD-07 para cada grupo detectado (incremento 4).

        Un grupo sin plantilla, o cuya explicación falle, se registra como
        error y se queda sin texto; los demás se explican igual (CA-07.3).
        """
        explicaciones: dict[str, Any] = {}
        for deteccion in resultado.detecciones:
            try:
                explicacion = explicar(
                    deteccion.grupo, deteccion.pico_cm1, catalogo, plantillas
                )
            except Exception:
                _registro.exception(
                    "educativo | grupo=%s | resultado=%s",
                    deteccion.grupo,
                    mensajes.EXPLICACION_NO_DISPONIBLE,
                )
                continue
            if not explicacion.disponible:
                _registro.error(
                    "educativo | grupo=%s | resultado=%s",
                    deteccion.grupo,
                    mensajes.EXPLICACION_NO_DISPONIBLE,
                )
                continue
            explicaciones[deteccion.grupo] = explicacion
        return explicaciones
    if modelo is MODELO_DEL_REPOSITORIO:
        modelo = _modelo_de_arranque(catalogo)
    motivo = motivo_para_solo_reglas(modelo, parametros)
    if motivo is not None:
        # D-16: la falta de modelo es una degradación anunciada, no un error.
        _registro.info("motor arranque | modo=reglas | motivo=%s", motivo)
        modelo = None
    else:
        _registro.info("motor arranque | modo=hibrido")

    aplicacion = FastAPI(
        title="E-VER Spectre Identifier",
        version="1.0.0-incremento-1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @aplicacion.exception_handler(RequestValidationError)
    async def peticion_sin_archivo(
        peticion: Request, error: RequestValidationError
    ) -> JSONResponse:
        """La petición no trae el campo `archivo`.

        FastAPI respondería un 422 describiendo el campo que falta y el tipo que
        esperaba: eso es información técnica, y la regla 2 dice que el usuario no
        la ve. Se cambia por el mensaje genérico de UT-02.

        El 400 es la única parte que el contrato de la sección 5 no nombra: no
        hay veredicto que emitir —no llegó archivo— y tampoco falló nada por
        dentro, así que ni 200 ni 500 encajan. Queda anotado para el equipo.
        """
        _registro.warning(
            "api peticion invalida | ruta=%s | resultado=%s",
            peticion.url.path,
            mensajes.FALLO_INTERNO,
        )
        return JSONResponse(
            status_code=CODIGO_PETICION_INVALIDA,
            content=rechazado(mensajes.FALLO_INTERNO, parametros),
        )

    @aplicacion.post(RUTA_VALIDAR)
    async def validar_espectro(archivo: UploadFile = File(...)) -> JSONResponse:
        """Recibe el archivo y devuelve el veredicto del contrato de la sección 5."""
        recepcion = None
        try:
            # MOD-02: aplica el tamaño de UT-03, lee por bloques y cierra la
            # subida. Nunca levanta por culpa del archivo.
            recepcion = await recibir(archivo, parametros)
            if not recepcion.aceptado:
                return JSONResponse(rechazado(recepcion.codigo, parametros))

            # MOD-03: formato (T-04) y requisitos (T-05). Solo ve el texto y el
            # nombre; nunca el archivo (contrato de la sección 5).
            resultado = validar(
                recepcion.nombre,
                recepcion.contenido,
                tamano_correcto=recepcion.tamano_correcto,
                configuracion=parametros,
            )
            if not resultado.valido:
                return JSONResponse(rechazado(resultado.codigo, parametros))

            return JSONResponse(aceptado(recepcion.nombre, recepcion.bytes_leidos))
        except Exception:
            # Cualquier cosa inesperada —incluido un código que no esté en
            # UT-02— sale por aquí: el usuario ve el mensaje genérico y el
            # detalle queda en el registro del servidor. El servicio sigue de
            # pie y atiende la siguiente petición (CA-02.4).
            _registro.exception(
                "api fallo interno | resultado=%s", mensajes.FALLO_INTERNO
            )
            return JSONResponse(
                status_code=CODIGO_FALLO_INTERNO,
                content=rechazado(mensajes.FALLO_INTERNO, parametros),
            )
        finally:
            # Suelta el contenido en cuanto termina la petición (RNF-09). El
            # recolector lo haría igual al salir de la función; decirlo aquí deja
            # la intención por escrito y de paso cubre el caso del error.
            del recepcion

    @aplicacion.post(RUTA_PROCESAR)
    async def procesar_espectro(archivo: UploadFile = File(...)) -> JSONResponse:
        """MOD-02, MOD-03 y MOD-04 en la misma petición (incremento 2).

        Un rechazo de cualquiera de los tres es un resultado del negocio: 200
        con el mensaje de UT-02. MOD-04 suma sus propios rechazos, por ejemplo
        la línea plana (CA-03.3) o la unidad que no se reconoce (D-10, D-11).
        """
        recepcion = None
        try:
            recepcion = await recibir(archivo, parametros)
            if not recepcion.aceptado:
                return JSONResponse(rechazado(recepcion.codigo, parametros))

            resultado = validar(
                recepcion.nombre,
                recepcion.contenido,
                tamano_correcto=recepcion.tamano_correcto,
                configuracion=parametros,
            )
            if not resultado.valido:
                return JSONResponse(rechazado(resultado.codigo, parametros))

            # MOD-04: solo ve el nombre y el texto ya aprobado.
            salida = procesar(recepcion.nombre, recepcion.contenido, parametros)
            if not salida.valido:
                return JSONResponse(rechazado(salida.codigo, parametros))

            return JSONResponse(procesado(recepcion.nombre, salida.espectro))
        except Exception:
            _registro.exception(
                "api fallo interno | ruta=%s | resultado=%s",
                RUTA_PROCESAR,
                mensajes.FALLO_INTERNO,
            )
            return JSONResponse(
                status_code=CODIGO_FALLO_INTERNO,
                content=rechazado(mensajes.FALLO_INTERNO, parametros),
            )
        finally:
            del recepcion

    limite_json = parametros.archivo.tamano_maximo_bytes * FACTOR_CUERPO_JSON

    @aplicacion.post(RUTA_ANALIZAR)
    async def analizar_espectro(peticion: Request) -> JSONResponse:
        """MOD-06 sobre el espectro que la página ya tiene (incremento 3).

        Un espectro que no tiene la forma del contrato se rechaza con 200 y
        ESPECTRO_INVALIDO antes de llegar al motor (D-17). Un fallo del motor
        responde 500 con ANALISIS_FALLIDO, el texto de CA-05.4. Que ningún
        grupo pase el umbral no es ninguna de las dos cosas: es un resultado
        con su aviso (CA-08).
        """
        try:
            cuerpo = await _leer_json(peticion, limite_json)
            espectro = espectro_desde(cuerpo, parametros)
            if espectro is None:
                _registro.warning(
                    "api analizar | resultado=%s", mensajes.ESPECTRO_INVALIDO
                )
                return JSONResponse(rechazado(mensajes.ESPECTRO_INVALIDO, parametros))

            resultado = identificar(espectro, modelo, catalogo, parametros)
            # El registro guarda qué se detectó, nunca el espectro (RNF-09).
            _registro.info(
                "api analizar | modo=%s | detecciones=%s",
                resultado.modo,
                ",".join(d.grupo for d in resultado.detecciones) or "ninguna",
            )
            return JSONResponse(
                analizado(
                    resultado,
                    catalogo,
                    parametros,
                    explicar_detecciones(resultado),
                )
            )
        except Exception:
            _registro.exception(
                "api fallo interno | ruta=%s | resultado=%s",
                RUTA_ANALIZAR,
                mensajes.ANALISIS_FALLIDO,
            )
            return JSONResponse(
                status_code=CODIGO_FALLO_INTERNO,
                content=rechazado(mensajes.ANALISIS_FALLIDO, parametros),
            )

    @aplicacion.post(RUTA_REPORTE)
    async def descargar_reporte(peticion: Request) -> Response:
        """MOD-08: el PDF del análisis (incremento 5).

        Vuelve a correr el motor y MOD-07 con el espectro que manda la página,
        así el reporte sale del mismo cálculo que se vio en pantalla. Responde
        el PDF armado en memoria; el servidor no lo guarda (RNF-09). Si la
        petición no trae lo necesario responde 200 con REPORTE_INVALIDO; si
        algo falla al generar, 500 con REPORTE_FALLIDO (CA-09.3).
        """
        try:
            cuerpo = await _leer_json(peticion, limite_json)
            datos = peticion_desde(cuerpo, parametros)
            if datos is None:
                _registro.warning("api reporte | resultado=%s", mensajes.REPORTE_INVALIDO)
                return JSONResponse(rechazado(mensajes.REPORTE_INVALIDO, parametros))

            resultado = identificar(datos.espectro, modelo, catalogo, parametros)
            analisis = analizado(
                resultado, catalogo, parametros, explicar_detecciones(resultado)
            )
            pdf = generar_pdf(
                DatosDelReporte(
                    nombre_archivo=datos.nombre,
                    fecha_hora=datos.fecha_hora,
                    zona=datos.zona,
                    analisis=analisis,
                    imagen_png=datos.imagen_png,
                )
            )
            _registro.info("api reporte | bytes=%d", len(pdf))
            descarga = _nombre_de_descarga(datos.nombre)
            return Response(
                content=pdf,
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{descarga}"'},
            )
        except Exception:
            _registro.exception(
                "api fallo interno | ruta=%s | resultado=%s",
                RUTA_REPORTE,
                mensajes.REPORTE_FALLIDO,
            )
            return JSONResponse(
                status_code=CODIGO_FALLO_INTERNO,
                content=rechazado(mensajes.REPORTE_FALLIDO, parametros),
            )

    @aplicacion.get("/")
    async def inicio() -> RedirectResponse:
        """La raíz lleva a la interfaz, que es lo único que hay que abrir."""
        return RedirectResponse(url=f"{RUTA_INTERFAZ}/")

    _montar_frontend(aplicacion, carpeta_frontend or CARPETA_FRONTEND)
    return aplicacion


def _montar_frontend(aplicacion: FastAPI, carpeta: Path) -> None:
    """Sirve `interfaz/` y `servicios/` tal como están en la carpeta dada.

    Se montan las dos carpetas por separado, y no toda la carpeta `frontend/`,
    por una razón concreta: así `frontend/pruebas/` (D-9) no queda publicado.
    """
    aplicacion.mount(
        RUTA_INTERFAZ,
        StaticFiles(directory=carpeta / "interfaz", html=True),
        name="interfaz",
    )
    aplicacion.mount(
        RUTA_SERVICIOS,
        StaticFiles(directory=carpeta / "servicios"),
        name="servicios",
    )
    aplicacion.mount(
        RUTA_VISOR,
        # check_dir=False: una copia del frontend sin estas carpetas (como la
        # de una prueba) sigue arrancando; solo no tendría gráfica.
        StaticFiles(directory=carpeta / "visor-espectro", check_dir=False),
        name="visor-espectro",
    )
    aplicacion.mount(
        RUTA_LIBRERIAS,
        StaticFiles(directory=carpeta / "vendor", check_dir=False),
        name="vendor",
    )


def __getattr__(nombre: str) -> Any:  # pragma: no cover - ayuda de importación
    """Avisa claro si alguien importa `aplicacion` esperando una instancia.

    No hay una aplicación creada al importar este módulo, a propósito: crearla
    lee UT-03, y eso no debe pasar por el solo hecho de importar. Se crea con
    `crear_aplicacion()`.
    """
    if nombre == "aplicacion":
        raise AttributeError(
            "backend.api no expone una aplicación ya creada: use "
            "crear_aplicacion() (o «uvicorn backend.api:crear_aplicacion "
            "--factory»)"
        )
    raise AttributeError(nombre)
