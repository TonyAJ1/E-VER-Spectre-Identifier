/*
 * Servicio de validación · la única llamada que MOD-01 hace al servidor en el
 * incremento 1 (contrato D-5, sección 5 del plan):
 *
 *   POST /api/validar · multipart/form-data · campo «archivo»
 *   200 → veredicto (aceptado o rechazado: un rechazo es un resultado, no un error)
 *   500 → fallo interno, con mensaje genérico de UT-02
 *
 * MOD-01 nunca llama a MOD-02 ni a MOD-03 directamente: todo pasa por backend/api/.
 * Este archivo no interpreta el veredicto; solo lo trae.
 */
(function () {
  "use strict";

  /** Ruta del contrato D-5. Relativa: el mismo servidor sirve la página y la API. */
  var RUTA_VALIDAR = "/api/validar";

  /** Nombre del campo del formulario que espera la API. */
  var CAMPO_ARCHIVO = "archivo";

  /**
   * Envía el archivo y devuelve una promesa con:
   *   { tipo: "veredicto", datos }  → la API contestó 200 (aceptado o rechazado)
   *   { tipo: "error", datos }      → la API contestó otro código (p. ej. 500);
   *                                    `datos` trae el mensaje de UT-02 si llegó
   *   { tipo: "sin-conexion" }      → no hubo respuesta del servidor
   */
  function validarArchivo(archivo) {
    var formulario = new FormData();
    formulario.append(CAMPO_ARCHIVO, archivo);

    return fetch(RUTA_VALIDAR, { method: "POST", body: formulario })
      .then(function (respuesta) {
        return respuesta
          .json()
          .catch(function () { return null; })
          .then(function (datos) {
            if (respuesta.status === 200 && datos) {
              return { tipo: "veredicto", datos: datos };
            }
            return { tipo: "error", datos: datos };
          });
      })
      .catch(function () {
        return { tipo: "sin-conexion" };
      });
  }

  window.EVER = window.EVER || {};
  window.EVER.servicios = window.EVER.servicios || {};
  window.EVER.servicios.validarArchivo = validarArchivo;
})();
