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
    verExplicacion: "Ver explicación",
    region: "Región característica",
    posicion: "Pico observado",
    sinPosicion: "El motor no reportó la posición exacta del pico.",
    rasgo: "Lo que lo delata",
    porQue: "Por qué corresponde a este grupo",
    resaltar: "Resaltar en la gráfica",
    nombreReporte: "reporte_analisis.pdf",
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

  var botonReporte = document.getElementById("boton-reporte");
  var reporteEstado = document.getElementById("reporte-estado");
  var reporteMensaje = document.getElementById("reporte-mensaje");
  var reporteAccion = document.getElementById("reporte-accion");

  // Incremento 5: lo que hace falta para pedir el reporte del último
  // análisis. El servidor no guarda nada, así que la página lo conserva.
  var nombreActual = null;
  var analisisActual = null;

  // El espectro procesado del último archivo aprobado. Es lo único que se
  // manda al motor; el archivo no se vuelve a subir.
  var espectroActual = null;

  var seccionGrafica = document.getElementById("grafica");
  var lienzoGrafica = document.getElementById("grafica-lienzo");
  var leyendaGrafica = document.getElementById("grafica-leyenda");

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
    nombreActual = null;
  }

  // Incremento 3: resultados del análisis.

  function quitarResaltado() {
    resaltados = [];
    window.EVER.visor.resaltar(lienzoGrafica, [], leyendaGrafica);
  }

  function ocultarAnalisis() {
    quitarResaltado();
    seccionAnalisis.hidden = true;
    seccionAnalisis.dataset.estado = "inicial";
    analisisLista.textContent = "";
  }

  function pintarAnalisis(estado, piezas) {
    quitarResaltado();
    ocultarReporte();
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

  // Incremento 4: la explicación de MOD-07, plegada hasta que el usuario la
  // abre. Todo se pinta con textContent.
  function armarExplicacion(explicacion) {
    var bloque = document.createElement("details");
    bloque.className = "explicacion";
    var resumen = document.createElement("summary");
    resumen.textContent = TEXTOS.verExplicacion;
    bloque.appendChild(resumen);

    if (!explicacion.disponible) {
      var aviso = document.createElement("p");
      aviso.className = "explicacion-no-disponible";
      aviso.textContent = explicacion.aviso;
      bloque.appendChild(aviso);
      return bloque;
    }

    var lista = document.createElement("dl");
    [
      [TEXTOS.region, explicacion.region],
      [TEXTOS.posicion, explicacion.posicion || TEXTOS.sinPosicion],
      [TEXTOS.rasgo, explicacion.rasgo],
      [TEXTOS.porQue, explicacion.por_que],
    ].forEach(function (par) {
      var termino = document.createElement("dt");
      termino.textContent = par[0];
      var definicion = document.createElement("dd");
      definicion.textContent = par[1];
      lista.appendChild(termino);
      lista.appendChild(definicion);
    });
    bloque.appendChild(lista);
    return bloque;
  }

  // Incremento 4: cada grupo tiene un botón para resaltarlo en la gráfica.
  // Se pueden resaltar varios a la vez.
  var resaltados = [];

  function armarBotonResaltar(deteccion) {
    var boton = document.createElement("button");
    boton.type = "button";
    boton.className = "boton-resaltar";
    boton.textContent = TEXTOS.resaltar;
    boton.setAttribute("aria-pressed", "false");
    boton.addEventListener("click", function () {
      var activo = boton.getAttribute("aria-pressed") === "true";
      boton.setAttribute("aria-pressed", activo ? "false" : "true");
      resaltados = resaltados.filter(function (marca) {
        return marca.grupo !== deteccion.grupo;
      });
      if (!activo) {
        resaltados.push({
          grupo: deteccion.grupo,
          nombre: deteccion.nombre,
          region_cm1: deteccion.region_cm1,
          pico_cm1: deteccion.pico_cm1,
        });
      }
      window.EVER.visor.resaltar(lienzoGrafica, resaltados, leyendaGrafica);
    });
    return boton;
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
      elemento.appendChild(armarBotonResaltar(deteccion));
      if (deteccion.explicacion) {
        elemento.appendChild(armarExplicacion(deteccion.explicacion));
      }
      analisisLista.appendChild(elemento);
    });
  }

  // Incremento 5: reporte PDF.

  function ocultarReporte() {
    analisisActual = null;
    botonReporte.hidden = true;
    reporteEstado.hidden = true;
  }

  function fechaLocal(fecha) {
    // La fecha y hora local con su diferencia respecto a UTC, en el formato
    // que entiende el servidor, por ejemplo 2026-11-23T15:41:00-06:00.
    function dos(n) { return (n < 10 ? "0" : "") + n; }
    var minutos = -fecha.getTimezoneOffset();
    var signo = minutos >= 0 ? "+" : "-";
    minutos = Math.abs(minutos);
    return fecha.getFullYear() + "-" + dos(fecha.getMonth() + 1) + "-" + dos(fecha.getDate()) +
      "T" + dos(fecha.getHours()) + ":" + dos(fecha.getMinutes()) + ":" + dos(fecha.getSeconds()) +
      signo + dos(Math.floor(minutos / 60)) + ":" + dos(minutos % 60);
  }

  function prepararReporte(resultado) {
    analisisActual = { resultado: resultado, fechaHora: fechaLocal(new Date()) };
    botonReporte.hidden = false;
    botonReporte.disabled = false;
  }

  function cuerpoDelReporte() {
    // T-26: la gráfica del reporte lleva resaltados todos los grupos
    // detectados, no solo los que el usuario marcó en pantalla.
    var marcasDelReporte = analisisActual.resultado.detecciones.map(function (d) {
      return { grupo: d.grupo, nombre: d.nombre, region_cm1: d.region_cm1, pico_cm1: d.pico_cm1 };
    });
    return {
      nombre_archivo: nombreActual,
      fecha_hora: analisisActual.fechaHora,
      imagen_png: window.EVER.visor.imagenParaReporte(espectroActual, marcasDelReporte),
      detecciones: analisisActual.resultado.detecciones.map(function (d) {
        return {
          grupo: d.grupo,
          confianza: d.confianza,
          region_cm1: d.region_cm1,
          pico_cm1: d.pico_cm1,
        };
      }),
    };
  }

  function descargar(archivo) {
    var enlace = document.createElement("a");
    var direccion = URL.createObjectURL(archivo);
    enlace.href = direccion;
    enlace.download = TEXTOS.nombreReporte;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    setTimeout(function () { URL.revokeObjectURL(direccion); }, 1000);
  }

  function mostrarFalloDelReporte(datos) {
    reporteEstado.hidden = false;
    poner(reporteMensaje, datos && datos.mensaje ? datos.mensaje : TEXTOS.sinConexionMensaje);
    poner(reporteAccion, datos && datos.accion ? datos.accion : TEXTOS.sinConexionAccion);
  }

  botonReporte.addEventListener("click", function () {
    if (!analisisActual) {
      return;
    }
    botonReporte.disabled = true;
    reporteEstado.hidden = true;
    window.EVER.servicios
      .pedirReporte(cuerpoDelReporte())
      .then(function (respuesta) {
        if (respuesta.tipo === "pdf") {
          descargar(respuesta.datos);
          return;
        }
        mostrarFalloDelReporte(respuesta.datos);
      })
      .finally(function () {
        // Los resultados siguen en pantalla y se puede volver a intentar.
        botonReporte.disabled = analisisActual === null;
      });
  });

  function mostrarResultadoDelAnalisis(respuesta) {
    if (respuesta.tipo === "resultado" && respuesta.datos.sin_detecciones) {
      // CA-08: el aviso viene de UT-02 y no se lista ningún grupo.
      var aviso = respuesta.datos.aviso || {};
      pintarAnalisis("sin-detecciones", {
        titulo: aviso.titulo,
        mensaje: aviso.mensaje,
        accion: aviso.accion,
      });
      return;
    }
    if (respuesta.tipo === "resultado") {
      mostrarDetecciones(respuesta.datos);
      prepararReporte(respuesta.datos);
      return;
    }
    if (respuesta.tipo === "error" && respuesta.datos && respuesta.datos.mensaje) {
      // CA-05.4: mensaje genérico de UT-02. El archivo sigue cargado.
      pintarAnalisis("error", {
        titulo: respuesta.datos.titulo,
        mensaje: respuesta.datos.mensaje,
        accion: respuesta.datos.accion,
      });
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
        nombreActual = veredicto.nombre;
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
    nombreActual = null;
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
