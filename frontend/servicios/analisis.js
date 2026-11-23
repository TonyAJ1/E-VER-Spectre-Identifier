/*
 * Servicio de análisis (incremento 3). Envía a POST /api/analizar el eje y la
 * intensidad que el servidor devolvió al validar el archivo. El archivo no se
 * vuelve a mandar: el motor solo trabaja con el vector normalizado.
 *
 * Devuelve una promesa con uno de estos objetos:
 *   tipo "resultado" cuando la API contestó 200, con las detecciones;
 *   tipo "error" cuando contestó otro código, con el mensaje de UT-02 si llegó;
 *   tipo "sin-conexion" cuando el servidor no respondió.
 */
(function () {
  "use strict";

  var RUTA_ANALIZAR = "/api/analizar";

  function analizar(espectro) {
    var cuerpo = JSON.stringify({
      eje_cm1: espectro.eje_cm1,
      intensidad: espectro.intensidad,
    });
    return fetch(RUTA_ANALIZAR, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: cuerpo,
    })
      .then(function (respuesta) {
        return respuesta
          .json()
          .catch(function () { return null; })
          .then(function (datos) {
            if (respuesta.status === 200 && datos) {
              return { tipo: "resultado", datos: datos };
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
  window.EVER.servicios.analizar = analizar;
})();
