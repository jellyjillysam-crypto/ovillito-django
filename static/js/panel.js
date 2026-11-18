/* Panel del administrador: gráficas (Chart.js) y mapa de clientes (Leaflet). */
(function () {
  "use strict";

  const COLOR = {
    marca: "#2A8059",
    marcaHover: "#358F66",
    marcaLavado: "rgba(42, 128, 89, 0.10)",
    grilla: "rgba(74, 40, 18, 0.10)",
    eje: "rgba(74, 40, 18, 0.25)",
    texto: "#6E5442",
    tinta: "#3B2414",
    superficie: "#FFFBEF",
  };
  const pesos = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
  const compacto = (v) => {
    if (v >= 1e6) return "$" + (v / 1e6).toLocaleString("es-CO", { maximumFractionDigits: 1 }) + " M";
    if (v >= 1000) return "$" + Math.round(v / 1000) + " mil";
    return "$" + v;
  };

  /* --- Gráficas -------------------------------------------------------------- */
  const fuenteDatos = document.getElementById("datos-graficas");
  if (window.Chart && fuenteDatos) {
    const datos = JSON.parse(fuenteDatos.textContent);
    Chart.defaults.font.family = "Nunito, system-ui, sans-serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = COLOR.texto;
    Chart.defaults.plugins.legend.display = false;
    Object.assign(Chart.defaults.plugins.tooltip, {
      backgroundColor: COLOR.superficie,
      borderColor: "rgba(74, 40, 18, 0.25)",
      borderWidth: 1,
      titleColor: COLOR.texto,
      titleFont: { weight: "600", size: 12 },
      bodyColor: COLOR.tinta,
      bodyFont: { weight: "800", size: 14 },
      padding: 10,
      cornerRadius: 10,
      displayColors: false,
      caretSize: 6,
    });

    // Línea vertical que sigue al puntero en la gráfica de líneas.
    const crucetaPlugin = {
      id: "cruceta",
      afterDatasetsDraw(chart, args, opciones) {
        if (!opciones || !opciones.activa) return;
        const activos = chart.tooltip && chart.tooltip.getActiveElements();
        if (!activos || !activos.length) return;
        const x = activos[0].element.x;
        const { top, bottom } = chart.chartArea;
        const ctx = chart.ctx;
        ctx.save();
        ctx.strokeStyle = "rgba(74, 40, 18, 0.35)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, top);
        ctx.lineTo(x, bottom);
        ctx.stroke();
        ctx.restore();
      },
    };

    // Valor escrito en la punta de cada barra (texto en color de tinta, no del dato).
    const valorPuntaPlugin = {
      id: "valorPunta",
      afterDatasetsDraw(chart, args, opciones) {
        if (!opciones || !opciones.activa) return;
        const ctx = chart.ctx;
        const horizontal = chart.options.indexAxis === "y";
        ctx.save();
        ctx.font = "700 12px Nunito, system-ui, sans-serif";
        ctx.fillStyle = COLOR.tinta;
        chart.getDatasetMeta(0).data.forEach((barra, i) => {
          const valor = chart.data.datasets[0].data[i];
          if (!valor) return;
          const texto = opciones.formato ? opciones.formato(valor) : String(valor);
          if (horizontal) {
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            ctx.fillText(texto, barra.x + 6, barra.y);
          } else {
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";
            ctx.fillText(texto, barra.x, barra.y - 5);
          }
        });
        ctx.restore();
      },
    };

    // Etiqueta del último valor en la gráfica de líneas.
    const valorFinalPlugin = {
      id: "valorFinal",
      afterDatasetsDraw(chart, args, opciones) {
        if (!opciones || !opciones.activa) return;
        const puntos = chart.getDatasetMeta(0).data;
        const ultimo = puntos[puntos.length - 1];
        if (!ultimo) return;
        const valor = chart.data.datasets[0].data[puntos.length - 1];
        const anterior = puntos[puntos.length - 2];
        // Si la línea llega bajando, la etiqueta va debajo del punto para no cruzarse con ella.
        const debajo = anterior && anterior.y < ultimo.y && ultimo.y + 24 < chart.chartArea.bottom;
        const ctx = chart.ctx;
        ctx.save();
        ctx.font = "800 12px Nunito, system-ui, sans-serif";
        ctx.fillStyle = COLOR.tinta;
        ctx.textAlign = "right";
        ctx.textBaseline = debajo ? "top" : "bottom";
        ctx.fillText(compacto(valor), ultimo.x - 4, debajo ? ultimo.y + 9 : ultimo.y - 9);
        ctx.restore();
      },
    };
    Chart.register(crucetaPlugin, valorPuntaPlugin, valorFinalPlugin);

    const vacio = (canvas, texto) => {
      const p = document.createElement("p");
      p.className = "texto-suave";
      p.style.margin = "auto";
      p.textContent = texto;
      canvas.parentElement.replaceChildren(p);
    };

    const ejeValores = (formato) => ({
      beginAtZero: true,
      grid: { color: COLOR.grilla, drawTicks: false },
      border: { display: false },
      ticks: { padding: 8, maxTicksLimit: 5, precision: 0, callback: formato || ((v) => v) },
    });
    const ejeCategorias = {
      grid: { display: false },
      border: { color: COLOR.eje },
      ticks: { color: COLOR.tinta, font: { weight: "700" } },
    };
    const barra = {
      backgroundColor: COLOR.marca,
      hoverBackgroundColor: COLOR.marcaHover,
      maxBarThickness: 24,
      borderRadius: 4,
      borderSkipped: "start",
    };

    // 1. Ingresos diarios (línea con lavado de área).
    const cIngresos = document.getElementById("grafica-ingresos");
    if (cIngresos) {
      const dias = datos.dias;
      if (!dias.some((d) => d.total > 0)) vacio(cIngresos, "Aún no hay ventas en los últimos 14 días.");
      else new Chart(cIngresos, {
        type: "line",
        data: {
          labels: dias.map((d) => d.etiqueta),
          datasets: [{
            data: dias.map((d) => d.total),
            borderColor: COLOR.marca,
            borderWidth: 2,
            backgroundColor: COLOR.marcaLavado,
            fill: true,
            cubicInterpolationMode: "monotone",
            pointRadius: (ctx) => (ctx.dataIndex === dias.length - 1 ? 4 : 0),
            pointBackgroundColor: COLOR.marca,
            pointBorderColor: COLOR.superficie,
            pointBorderWidth: 2,
            pointHoverRadius: 5,
            pointHoverBorderWidth: 2,
            pointHitRadius: 16,
          }],
        },
        options: {
          maintainAspectRatio: false,
          interaction: { mode: "index", intersect: false },
          layout: { padding: { top: 18, right: 6 } },
          scales: {
            y: ejeValores(compacto),
            x: { grid: { display: false }, border: { color: COLOR.eje }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 7 } },
          },
          plugins: {
            cruceta: { activa: true },
            valorFinal: { activa: true },
            tooltip: {
              callbacks: {
                title: (items) => `Día ${items[0].label}`,
                label: (item) => pesos.format(item.raw),
                afterLabel: (item) => `${dias[item.dataIndex].pedidos} pedido${dias[item.dataIndex].pedidos === 1 ? "" : "s"}`,
              },
            },
          },
        },
      });
    }

    // 2. Unidades por categoría (barras horizontales, de mayor a menor).
    const cCategorias = document.getElementById("grafica-categorias");
    if (cCategorias) {
      const filas = datos.categorias;
      if (!filas.length) vacio(cCategorias, "Aún no hay ventas.");
      else new Chart(cCategorias, {
        type: "bar",
        data: { labels: filas.map((f) => f.etiqueta), datasets: [{ data: filas.map((f) => f.valor), ...barra }] },
        options: {
          indexAxis: "y",
          maintainAspectRatio: false,
          layout: { padding: { right: 30 } },
          scales: { x: ejeValores(), y: ejeCategorias },
          plugins: {
            valorPunta: { activa: true },
            tooltip: {
              callbacks: {
                label: (item) => `${item.raw} unidades`,
                afterLabel: (item) => pesos.format(filas[item.dataIndex].ingresos),
              },
            },
          },
        },
      });
    }

    // 3. Calificaciones 1–5 (columnas).
    const cCalif = document.getElementById("grafica-calificaciones");
    if (cCalif) {
      const filas = datos.calificaciones;
      if (!filas.some((f) => f.valor > 0)) vacio(cCalif, "Aún no hay respuestas.");
      else new Chart(cCalif, {
        type: "bar",
        data: { labels: filas.map((f) => f.etiqueta), datasets: [{ data: filas.map((f) => f.valor), ...barra }] },
        options: {
          maintainAspectRatio: false,
          layout: { padding: { top: 20 } },
          scales: { y: ejeValores(), x: ejeCategorias },
          plugins: {
            valorPunta: { activa: true },
            tooltip: { callbacks: { title: (i) => `Calificación ${i[0].label}`, label: (i) => `${i.raw} respuesta${i.raw === 1 ? "" : "s"}` } },
          },
        },
      });
    }

    // 4. ¿Cómo nos conocieron? (barras horizontales).
    const cCanales = document.getElementById("grafica-canales");
    if (cCanales) {
      const filas = datos.canales;
      if (!filas.length) vacio(cCanales, "Aún no hay respuestas.");
      else new Chart(cCanales, {
        type: "bar",
        data: { labels: filas.map((f) => f.etiqueta), datasets: [{ data: filas.map((f) => f.valor), ...barra }] },
        options: {
          indexAxis: "y",
          maintainAspectRatio: false,
          layout: { padding: { right: 24 } },
          scales: { x: ejeValores(), y: ejeCategorias },
          plugins: {
            valorPunta: { activa: true },
            tooltip: { callbacks: { label: (i) => `${i.raw} respuesta${i.raw === 1 ? "" : "s"}` } },
          },
        },
      });
    }
  }

  /* --- Mapa de clientes ------------------------------------------------------ */
  const contenedorMapa = document.getElementById("mapa-panel");
  const fuenteMapa = document.getElementById("datos-mapa-panel");
  if (window.L && contenedorMapa && fuenteMapa) {
    const tienda = window.OVILLITO_TIENDA;
    const puntos = JSON.parse(fuenteMapa.textContent).puntos;
    const mapa = L.map(contenedorMapa, { scrollWheelZoom: false }).setView([tienda.lat, tienda.lng], 12);
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(mapa);

    [1000, 3000, 5000].forEach((radio) => {
      L.circle([tienda.lat, tienda.lng], { radius: radio, color: "#4A2812", weight: 1, opacity: 0.35, fill: false, interactive: false }).addTo(mapa);
    });

    const icono = L.divIcon({
      className: "",
      html: `<div class="marcador-tienda" style="width:46px;height:46px"><img src="${window.OVILLITO_ISOTIPO}" alt="" style="width:30px"></div>`,
      iconSize: [46, 46],
      iconAnchor: [23, 23],
    });
    const etiquetaTienda = document.createElement("strong");
    etiquetaTienda.textContent = tienda.nombre;
    L.marker([tienda.lat, tienda.lng], { icon: icono, alt: tienda.nombre, zIndexOffset: 1000 }).addTo(mapa).bindTooltip(etiquetaTienda);

    const limites = [[tienda.lat, tienda.lng]];
    puntos.forEach((p) => {
      const etiqueta = document.createElement("span");
      etiqueta.textContent = `${p.nombre} · ${String(p.distancia).replace(".", ",")} km`;
      L.circleMarker([p.lat, p.lng], {
        radius: 7, color: COLOR.superficie, weight: 2, fillColor: COLOR.marca, fillOpacity: 1,
      }).addTo(mapa).bindTooltip(etiqueta);
      limites.push([p.lat, p.lng]);
    });
    if (limites.length > 1) mapa.fitBounds(limites, { padding: [30, 30], maxZoom: 14 });
  }
})();
