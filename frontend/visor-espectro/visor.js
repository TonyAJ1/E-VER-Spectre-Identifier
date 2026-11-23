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
 */
(function () {
  "use strict";

  var TEXTOS = {
    ejeHorizontal: "Número de onda (cm⁻¹)",
    ejeVertical: "Absorbancia normalizada",
    serie: "Espectro",
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

  window.EVER = window.EVER || {};
  window.EVER.visor = {
    dibujar: dibujar,
    limpiar: limpiar,
    grafica: function (contenedor) {
      return graficas.get(contenedor) || null;
    },
  };
})();
