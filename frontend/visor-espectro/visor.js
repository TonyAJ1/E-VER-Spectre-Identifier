/*
 * MOD-05, visualizador de espectro (tareas T-12 y T-13).
 *
 * Dibuja el espectro que entrega MOD-04 con Chart.js. El eje horizontal es el
 * número de onda en cm⁻¹ y va invertido, del mayor al menor, como se
 * acostumbra en infrarrojo. El eje vertical es la absorbancia normalizada
 * entre 0 y 1.
 *
 * Este archivo no sabe nada de archivos ni de la API. Recibe un objeto con
 * eje_cm1, intensidad y rango_medido_cm1 y lo dibuja dentro del contenedor que
 * le pasen. Los límites del eje salen de los datos, no se escriben aquí,
 * porque el rango de la rejilla vive en UT-03.
 *
 * Los puntos que caen fuera del tramo medido no se dibujan. Así la gráfica no
 * muestra valores que nadie midió.
 *
 * Desde el incremento 4 también resalta la región de cada grupo detectado y
 * marca la posición de su pico.
 */
(function () {
  "use strict";

  var TEXTOS = {
    ejeHorizontal: "Número de onda (cm⁻¹)",
    ejeVertical: "Absorbancia normalizada",
    serie: "Espectro",
  };

  // Incremento 4: resaltado de regiones y picos (T-23). Es un complemento
  // pequeño de Chart.js escrito aquí mismo, para no agregar otra librería.
  // Dibuja una franja de color sobre la región de cada grupo marcado y, si
  // el motor dio la posición del pico, una línea punteada en ese número de
  // onda.
  var COLOR_RESALTADO = "#e07a1f";

  // T-24: cada grupo tiene su propio color, así dos regiones que se enciman,
  // como O–H y N–H, se distinguen. Los colores se eligieron para que se
  // separen bien entre sí sobre fondo claro y oscuro.
  var COLORES_POR_GRUPO = {
    "GF-01": "#d1495b",
    "GF-02": "#2e86ab",
    "GF-03": "#7b61c9",
    "GF-04": "#e07a1f",
    "GF-05": "#2a9d8f",
    "GF-06": "#b8860b",
    "GF-07": "#c2549d",
  };

  var TEXTO_SIN_PICO = "región completa, sin posición exacta del pico";

  function colorDe(grupo) {
    return COLORES_POR_GRUPO[grupo] || COLOR_RESALTADO;
  }

  var complementoResaltado = {
    id: "resaltado",
    beforeDatasetsDraw: function (grafica, argumentos, opciones) {
      var marcas = (opciones && opciones.marcas) || [];
      if (!marcas.length) {
        return;
      }
      var area = grafica.chartArea;
      var ejeX = grafica.scales.x;
      var contexto = grafica.ctx;
      contexto.save();
      marcas.forEach(function (marca) {
        var color = marca.color || COLOR_RESALTADO;
        var a = ejeX.getPixelForValue(marca.region_cm1[0]);
        var b = ejeX.getPixelForValue(marca.region_cm1[1]);
        var izquierda = Math.max(area.left, Math.min(a, b));
        var derecha = Math.min(area.right, Math.max(a, b));
        contexto.globalAlpha = 0.25;
        contexto.fillStyle = color;
        contexto.fillRect(izquierda, area.top, derecha - izquierda, area.bottom - area.top);
        contexto.globalAlpha = 1;
        if (marca.pico_cm1 !== null && marca.pico_cm1 !== undefined) {
          var x = ejeX.getPixelForValue(marca.pico_cm1);
          contexto.strokeStyle = color;
          contexto.lineWidth = 2;
          contexto.setLineDash([5, 4]);
          contexto.beginPath();
          contexto.moveTo(x, area.top);
          contexto.lineTo(x, area.bottom);
          contexto.stroke();
          contexto.setLineDash([]);
        }
      });
      contexto.restore();
    },
  };

  // Una gráfica por contenedor. Se guarda para poder borrarla antes de dibujar
  // otra o cuando el archivo nuevo no pasa la validación.
  var graficas = new WeakMap();

  function colores() {
    var estilo = getComputedStyle(document.documentElement);
    function leer(nombre, siFalta) {
      var valor = estilo.getPropertyValue(nombre).trim();
      return valor || siFalta;
    }
    return {
      linea: leer("--grafica-linea", "#1f5fbf"),
      texto: leer("--texto-suave", "#556070"),
      reticula: leer("--borde", "#d5dae1"),
    };
  }

  function puntos(espectro) {
    var desde = espectro.rango_medido_cm1[0];
    var hasta = espectro.rango_medido_cm1[1];
    var lista = [];
    for (var i = 0; i < espectro.eje_cm1.length; i++) {
      var onda = espectro.eje_cm1[i];
      var medido = onda >= desde && onda <= hasta;
      lista.push({ x: onda, y: medido ? espectro.intensidad[i] : null });
    }
    return lista;
  }

  function limpiar(contenedor) {
    var grafica = graficas.get(contenedor);
    if (grafica) {
      grafica.destroy();
      graficas.delete(contenedor);
    }
    contenedor.textContent = "";
  }

  function dibujar(contenedor, espectro) {
    limpiar(contenedor);
    var lienzo = document.createElement("canvas");
    lienzo.setAttribute("role", "img");
    lienzo.setAttribute("aria-label", "Gráfica del espectro infrarrojo");
    contenedor.appendChild(lienzo);

    var eje = espectro.eje_cm1;
    var mayor = Math.max(eje[0], eje[eje.length - 1]);
    var menor = Math.min(eje[0], eje[eje.length - 1]);
    var tono = colores();

    var grafica = new window.Chart(lienzo, {
      type: "line",
      plugins: [complementoResaltado],
      data: {
        datasets: [
          {
            label: TEXTOS.serie,
            data: puntos(espectro),
            borderColor: tono.linea,
            borderWidth: 1.5,
            pointRadius: 0,
            spanGaps: false,
            fill: false,
          },
        ],
      },
      options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        parsing: false,
        normalized: true,
        plugins: {
          resaltado: { marcas: [] },
          legend: { display: false },
          tooltip: { intersect: false, mode: "nearest", axis: "x" },
        },
        scales: {
          x: {
            type: "linear",
            reverse: true,
            min: menor,
            max: mayor,
            title: { display: true, text: TEXTOS.ejeHorizontal, color: tono.texto },
            // En un celular de 360 px caben pocas etiquetas. Se limitan, no
            // se giran y se escriben sin separador de miles para que se lean.
            ticks: {
              color: tono.texto,
              maxTicksLimit: 6,
              maxRotation: 0,
              autoSkipPadding: 8,
              callback: function (valor) {
                return String(Math.round(valor));
              },
            },
            grid: { color: tono.reticula },
          },
          y: {
            min: 0,
            max: 1,
            title: { display: true, text: TEXTOS.ejeVertical, color: tono.texto },
            ticks: { color: tono.texto, maxTicksLimit: 6 },
            grid: { color: tono.reticula },
          },
        },
      },
    });
    graficas.set(contenedor, grafica);
    return grafica;
  }

  /**
   * Marca sobre la gráfica la región y el pico de los grupos que se le pasen.
   * Cada marca trae grupo, region_cm1 y pico_cm1, que puede venir vacío.
   * Una lista vacía quita todas las marcas.
   */
  function resaltar(contenedor, marcas, leyenda) {
    var conColor = marcas.map(function (marca) {
      return Object.assign({}, marca, { color: colorDe(marca.grupo) });
    });
    if (leyenda) {
      pintarLeyenda(leyenda, conColor);
    }
    var grafica = graficas.get(contenedor);
    if (!grafica) {
      return;
    }
    grafica.options.plugins.resaltado.marcas = conColor;
    grafica.update("none");
  }

  // La leyenda dice qué color es de qué grupo y avisa cuando un grupo no
  // tiene posición exacta del pico, porque entonces se resalta la región
  // completa (CA-06.3).
  function pintarLeyenda(leyenda, marcas) {
    leyenda.textContent = "";
    leyenda.hidden = marcas.length === 0;
    marcas.forEach(function (marca) {
      var elemento = document.createElement("li");
      elemento.className = "leyenda-elemento";
      elemento.dataset.grupo = marca.grupo;
      var muestra = document.createElement("span");
      muestra.className = "leyenda-muestra";
      muestra.style.backgroundColor = marca.color;
      var texto = document.createElement("span");
      var sinPico = marca.pico_cm1 === null || marca.pico_cm1 === undefined;
      texto.textContent = (marca.nombre || marca.grupo) + (sinPico ? " (" + TEXTO_SIN_PICO + ")" : "");
      elemento.appendChild(muestra);
      elemento.appendChild(texto);
      leyenda.appendChild(elemento);
    });
  }

  // Incremento 5 (T-26): la gráfica para el reporte PDF. Se dibuja aparte,
  // fuera de la pantalla y con colores claros fijos, para que se vea igual en
  // el papel aunque la página esté en modo oscuro. Lleva resaltados todos los
  // grupos que se le pasen y devuelve la imagen PNG como texto en base 64.
  var ANCHO_IMAGEN = 900;
  var ALTO_IMAGEN = 420;

  var complementoFondoBlanco = {
    id: "fondoBlanco",
    beforeDraw: function (grafica) {
      var contexto = grafica.ctx;
      contexto.save();
      contexto.fillStyle = "#ffffff";
      contexto.fillRect(0, 0, grafica.width, grafica.height);
      contexto.restore();
    },
  };

  function imagenParaReporte(espectro, marcasDelReporte) {
    var caja = document.createElement("div");
    caja.style.position = "fixed";
    caja.style.left = "-10000px";
    caja.style.top = "0";
    caja.style.width = ANCHO_IMAGEN + "px";
    caja.style.height = ALTO_IMAGEN + "px";
    var lienzo = document.createElement("canvas");
    lienzo.width = ANCHO_IMAGEN;
    lienzo.height = ALTO_IMAGEN;
    caja.appendChild(lienzo);
    document.body.appendChild(caja);

    var eje = espectro.eje_cm1;
    var mayor = Math.max(eje[0], eje[eje.length - 1]);
    var menor = Math.min(eje[0], eje[eje.length - 1]);
    var texto = "#333333";
    var reticula = "#dddddd";
    var conColor = marcasDelReporte.map(function (marca) {
      return Object.assign({}, marca, { color: colorDe(marca.grupo) });
    });

    var grafica = new window.Chart(lienzo, {
      type: "line",
      plugins: [complementoFondoBlanco, complementoResaltado],
      data: {
        datasets: [
          {
            data: puntos(espectro),
            borderColor: "#1f5fbf",
            borderWidth: 1.5,
            pointRadius: 0,
            spanGaps: false,
            fill: false,
          },
        ],
      },
      options: {
        animation: false,
        responsive: false,
        devicePixelRatio: 2,
        parsing: false,
        plugins: {
          resaltado: { marcas: conColor },
          legend: { display: false },
          tooltip: { enabled: false },
        },
        scales: {
          x: {
            type: "linear",
            reverse: true,
            min: menor,
            max: mayor,
            title: { display: true, text: TEXTOS.ejeHorizontal, color: texto },
            ticks: {
              color: texto,
              maxRotation: 0,
              callback: function (valor) {
                return String(Math.round(valor));
              },
            },
            grid: { color: reticula },
          },
          y: {
            min: 0,
            max: 1,
            title: { display: true, text: TEXTOS.ejeVertical, color: texto },
            ticks: { color: texto },
            grid: { color: reticula },
          },
        },
      },
    });
    var imagen = grafica.toBase64Image("image/png");
    grafica.destroy();
    caja.remove();
    return imagen;
  }

  function marcas(contenedor) {
    var grafica = graficas.get(contenedor);
    return grafica ? grafica.options.plugins.resaltado.marcas.slice() : [];
  }

  window.EVER = window.EVER || {};
  window.EVER.visor = {
    dibujar: dibujar,
    limpiar: limpiar,
    resaltar: resaltar,
    marcas: marcas,
    imagenParaReporte: imagenParaReporte,
    grafica: function (contenedor) {
      return graficas.get(contenedor) || null;
    },
  };
})();
