/*
 * MOD-01 · Interfaz mínima (T-06).
 *
 * Flujo: el usuario elige un archivo → «Validar archivo» → se envía a la API →
 * se muestra el veredicto:
 *   - aceptado: aviso de documento aprobado, nombre del archivo y «Analizar»
 *     habilitado, sin acción (D-4);
 *   - rechazado: título, motivo y acción tal como los manda UT-02 (RNF-01).
 *
 * Los textos de rechazo NO se escriben aquí: llegan del servidor (UT-02). Lo
 * único propio de la interfaz son los rótulos de la página y el aviso de «sin
 * conexión», que no puede venir del servidor porque justamente no respondió.
 *
 * Todo dato que viene del servidor o del usuario (incluido el nombre del
 * archivo) se pinta con textContent, nunca como HTML.
 */
(function () {
  "use strict";

  var TEXTOS = {
    validando: "Revisando el archivo…",
    aprobado: "Documento aprobado",
    aprobadoMensaje: "El archivo es válido. Ya puede continuar con «Analizar».",
    sinConexionTitulo: "No hay conexión con el servidor",
    sinConexionMensaje: "No se pudo enviar el archivo para revisarlo.",
    sinConexionAccion: "Revise su conexión y vuelva a intentarlo en unos momentos.",
    analizando: "Analizando el espectro…",
    gruposDetectados: "Grupos funcionales detectados",
  };

  var formulario = document.getElementById("formulario");
  var selector = document.getElementById("archivo");
  var botonValidar = document.getElementById("boton-validar");
  var botonAnalizar = document.getElementById("boton-analizar");
  var resultado = document.getElementById("resultado");
  var titulo = document.getElementById("resultado-titulo");
  var nombre = document.getElementById("resultado-nombre");
  var mensaje = document.getElementById("resultado-mensaje");
  var accion = document.getElementById("resultado-accion");
  var seccionAnalisis = document.getElementById("analisis");
  var analisisTitulo = document.getElementById("analisis-titulo");
  var analisisMensaje = document.getElementById("analisis-mensaje");
  var analisisAccion = document.getElementById("analisis-accion");
  var analisisLista = document.getElementById("analisis-lista");

  // El espectro procesado del último archivo aprobado. Es lo único que se
  // manda al motor; el archivo no se vuelve a subir.
  var espectroActual = null;

  var seccionGrafica = document.getElementById("grafica");
  var lienzoGrafica = document.getElementById("grafica-lienzo");

  // Incremento 2: la gráfica solo existe junto a un archivo aprobado. En
  // cualquier otro estado se borra, para no dejar una gráfica vieja o vacía.
  function ocultarGrafica() {
    window.EVER.visor.limpiar(lienzoGrafica);
    seccionGrafica.hidden = true;
  }

  function mostrarGrafica(espectro) {
    seccionGrafica.hidden = false;
    window.EVER.visor.dibujar(lienzoGrafica, espectro);
  }

  /** Pinta el área de resultado. Los campos vacíos se ocultan. */
  function mostrar(estado, piezas) {
    resultado.hidden = false;
    resultado.dataset.estado = estado;
    poner(titulo, piezas.titulo);
    poner(nombre, piezas.nombre);
    poner(mensaje, piezas.mensaje);
    poner(accion, piezas.accion);
    botonAnalizar.disabled = estado !== "aceptado";
    ocultarGrafica();
    ocultarAnalisis();
    espectroActual = null;
  }

  // Incremento 3: resultados del análisis.

  function ocultarAnalisis() {
    seccionAnalisis.hidden = true;
    seccionAnalisis.dataset.estado = "inicial";
    analisisLista.textContent = "";
  }

  function pintarAnalisis(estado, piezas) {
    seccionAnalisis.hidden = false;
    seccionAnalisis.dataset.estado = estado;
    poner(analisisTitulo, piezas.titulo);
    poner(analisisMensaje, piezas.mensaje);
    poner(analisisAccion, piezas.accion);
    analisisLista.textContent = "";
  }

  function textoPorcentaje(valor) {
    return String(valor).replace(".", ",") + " %";
  }

  function mostrarDetecciones(resultado) {
    pintarAnalisis("detecciones", { titulo: TEXTOS.gruposDetectados });
    resultado.detecciones.forEach(function (deteccion) {
      var elemento = document.createElement("li");
      elemento.className = "deteccion";
      elemento.dataset.grupo = deteccion.grupo;

      var nombreGrupo = document.createElement("span");
      nombreGrupo.className = "deteccion-nombre";
      nombreGrupo.textContent = deteccion.nombre;

      var confianza = document.createElement("span");
      confianza.className = "deteccion-confianza";
      confianza.textContent = textoPorcentaje(deteccion.porcentaje);

      var familias = document.createElement("span");
      familias.className = "deteccion-familias";
      familias.textContent = deteccion.familias;

      elemento.appendChild(nombreGrupo);
      elemento.appendChild(confianza);
      elemento.appendChild(familias);
      analisisLista.appendChild(elemento);
    });
  }

  function mostrarResultadoDelAnalisis(respuesta) {
    if (respuesta.tipo === "resultado") {
      mostrarDetecciones(respuesta.datos);
      return;
    }
    pintarAnalisis("error", {
      titulo: TEXTOS.sinConexionTitulo,
      mensaje: TEXTOS.sinConexionMensaje,
      accion: TEXTOS.sinConexionAccion,
    });
  }

  function poner(elemento, texto) {
    elemento.textContent = texto || "";
    elemento.hidden = !texto;
  }

  function mostrarVeredicto(veredicto) {
    if (veredicto.valido === true) {
      mostrar("aceptado", {
        titulo: TEXTOS.aprobado,
        nombre: veredicto.nombre,
        mensaje: TEXTOS.aprobadoMensaje,
      });
      if (veredicto.espectro) {
        espectroActual = veredicto.espectro;
        mostrarGrafica(veredicto.espectro);
      }
      return;
    }
    mostrar("rechazado", {
      titulo: veredicto.titulo,
      mensaje: veredicto.mensaje,
      accion: veredicto.accion,
    });
  }

  function mostrarRespuesta(respuesta) {
    if (respuesta.tipo === "veredicto") {
      mostrarVeredicto(respuesta.datos);
      return;
    }
    if (respuesta.tipo === "error" && respuesta.datos && respuesta.datos.mensaje) {
      // 500 con el mensaje genérico de UT-02: se muestra tal cual.
      mostrar("error", {
        titulo: respuesta.datos.titulo,
        mensaje: respuesta.datos.mensaje,
        accion: respuesta.datos.accion,
      });
      return;
    }
    mostrar("error", {
      titulo: TEXTOS.sinConexionTitulo,
      mensaje: TEXTOS.sinConexionMensaje,
      accion: TEXTOS.sinConexionAccion,
    });
  }

  selector.addEventListener("change", function () {
    botonValidar.disabled = selector.files.length === 0;
    // Un archivo nuevo deja sin efecto el veredicto anterior.
    resultado.hidden = true;
    resultado.dataset.estado = "inicial";
    botonAnalizar.disabled = true;
    ocultarGrafica();
    ocultarAnalisis();
    espectroActual = null;
  });

  formulario.addEventListener("submit", function (evento) {
    evento.preventDefault();
    var archivo = selector.files[0];
    if (!archivo) {
      return;
    }

    botonValidar.disabled = true;
    mostrar("validando", { titulo: TEXTOS.validando });

    window.EVER.servicios
      .validarArchivo(archivo)
      .then(mostrarRespuesta)
      .finally(function () {
        botonValidar.disabled = selector.files.length === 0;
      });
  });

  botonAnalizar.addEventListener("click", function () {
    if (!espectroActual) {
      return;
    }
    botonAnalizar.disabled = true;
    pintarAnalisis("analizando", { titulo: TEXTOS.analizando });
    window.EVER.servicios
      .analizar(espectroActual)
      .then(mostrarResultadoDelAnalisis)
      .finally(function () {
        // El archivo sigue cargado: se puede volver a analizar.
        botonAnalizar.disabled = espectroActual === null;
      });
  });
})();
