/*
 * Servicio del reporte (incremento 5). Envía a POST /api/reporte lo que el
 * servidor necesita para armar el PDF y lo regresa como archivo.
 *
 * Devuelve una promesa con uno de estos objetos:
 *   tipo "pdf" con el archivo en datos cuando la API contestó 200;
 *   tipo "error" con el mensaje de UT-02 si llegó;
 *   tipo "sin-conexion" cuando el servidor no respondió.
 */
(function () {
  "use strict";

  var RUTA_REPORTE = "/api/reporte";

  function pedirReporte(cuerpo) {
    return fetch(RUTA_REPORTE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    })
      .then(function (respuesta) {
        if (respuesta.status === 200) {
          return respuesta.blob().then(function (archivo) {
            return { tipo: "pdf", datos: archivo };
          });
        }
        return respuesta
          .json()
          .catch(function () { return null; })
          .then(function (datos) {
            return { tipo: "error", datos: datos };
          });
      })
      .catch(function () {
        return { tipo: "sin-conexion" };
      });
  }

  window.EVER = window.EVER || {};
  window.EVER.servicios = window.EVER.servicios || {};
  window.EVER.servicios.pedirReporte = pedirReporte;
})();
