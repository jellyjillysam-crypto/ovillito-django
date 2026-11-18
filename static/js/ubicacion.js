/* Captura de ubicación (Geolocation API) y mapa con la distancia a la tienda (Leaflet). */
(function () {
  "use strict";
  const { $, enviar, toast } = window.Ovillito;
  const datos = JSON.parse(document.getElementById("datos-mapa").textContent);
  const tienda = datos.tienda;
  const boton = $("[data-capturar]");
  const estado = $("[data-estado] span");

  const mapa = L.map("mapa", { scrollWheelZoom: false }).setView([tienda.lat, tienda.lng], 14);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(mapa);

  function textoPopup(titulo, detalle) {
    const caja = document.createElement("div");
    const fuerte = document.createElement("strong");
    fuerte.textContent = titulo;
    caja.appendChild(fuerte);
    if (detalle) {
      caja.appendChild(document.createElement("br"));
      caja.appendChild(document.createTextNode(detalle));
    }
    return caja;
  }

  const iconoTienda = L.divIcon({
    className: "",
    html: `<div class="marcador-tienda" style="width:54px;height:54px"><img src="${window.OVILLITO_ISOTIPO}" alt=""></div>`,
    iconSize: [54, 54],
    iconAnchor: [27, 27],
  });
  L.marker([tienda.lat, tienda.lng], { icon: iconoTienda, title: tienda.nombre, alt: tienda.nombre })
    .addTo(mapa)
    .bindPopup(textoPopup(tienda.nombre, tienda.direccion));
  L.circle([tienda.lat, tienda.lng], { radius: 1000, color: "#1F5C3F", weight: 1, fillOpacity: 0.05 }).addTo(mapa);

  const iconoCliente = L.divIcon({
    className: "",
    html: '<div class="marcador-cliente" style="width:40px;height:40px">Tú</div>',
    iconSize: [40, 40],
    iconAnchor: [20, 20],
  });
  let marcador = null;
  let linea = null;
  let circuloPrecision = null;

  function mostrar(lat, lng, precision) {
    if (marcador) marcador.setLatLng([lat, lng]);
    else marcador = L.marker([lat, lng], { icon: iconoCliente, title: "Tu ubicación", alt: "Tu ubicación" }).addTo(mapa);
    if (linea) linea.setLatLngs([[lat, lng], [tienda.lat, tienda.lng]]);
    else linea = L.polyline([[lat, lng], [tienda.lat, tienda.lng]], { color: "#4A2812", weight: 3, opacity: 0.8 }).addTo(mapa);
    if (circuloPrecision) { mapa.removeLayer(circuloPrecision); circuloPrecision = null; }
    if (precision && precision < 2000) {
      circuloPrecision = L.circle([lat, lng], { radius: precision, color: "#2A8059", weight: 1, fillOpacity: 0.08 }).addTo(mapa);
    }
    mapa.fitBounds(L.latLngBounds([[lat, lng], [tienda.lat, tienda.lng]]), { padding: [60, 60], maxZoom: 16 });
  }

  function actualizarPanel(r) {
    $("[data-distancia]").textContent = r.distancia_texto;
    $("[data-mensaje]").textContent = r.mensaje;
    $("[data-min-caminando]").textContent = r.minutos.caminando;
    $("[data-min-bicicleta]").textContent = r.minutos.bicicleta;
    $("[data-min-carro]").textContent = r.minutos.carro;
    const precision = r.precision ? `, ±${Math.round(r.precision)} m` : "";
    estado.textContent = `Ubicación guardada el ${r.fecha} (${r.origen.toLowerCase()}${precision}).`;
    const ruta = $("[data-ruta]");
    ruta.href = `https://www.google.com/maps/dir/?api=1&origin=${r.latitud},${r.longitud}&destination=${tienda.lat},${tienda.lng}`;
  }

  async function guardar(latitud, longitud, precision, origen) {
    try {
      const r = await enviar(boton.dataset.url, { json: { latitud, longitud, precision, origen } });
      if (!r.ok) throw new Error(r.datos.error || "No se pudo guardar la ubicación.");
      mostrar(latitud, longitud, precision);
      actualizarPanel(r.datos);
      toast(`Estás a ${r.datos.distancia_texto} de la tienda.`);
    } catch (e) {
      estado.textContent = e.message;
      toast(e.message, "error");
    }
  }

  if (datos.ultima) mostrar(datos.ultima.lat, datos.ultima.lng, null);

  const ERRORES = {
    1: "No diste permiso para usar tu ubicación. Actívalo en el navegador o haz clic en el mapa.",
    2: "No pudimos determinar tu ubicación. Intenta de nuevo o haz clic en el mapa.",
    3: "La ubicación tardó demasiado. Intenta de nuevo o haz clic en el mapa.",
  };

  boton.addEventListener("click", () => {
    if (!("geolocation" in navigator)) {
      estado.textContent = "Tu navegador no permite obtener la ubicación. Haz clic en el mapa para marcarla.";
      return;
    }
    if (!window.isSecureContext) {
      estado.textContent = "El GPS solo funciona en https:// o en localhost. Haz clic en el mapa para marcar tu ubicación.";
      return;
    }
    boton.disabled = true;
    estado.textContent = "Buscando tu ubicación…";
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        boton.disabled = false;
        guardar(pos.coords.latitude, pos.coords.longitude, pos.coords.accuracy, "gps");
      },
      (err) => {
        boton.disabled = false;
        estado.textContent = ERRORES[err.code] || "No se pudo obtener la ubicación.";
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 }
    );
  });

  mapa.on("click", (e) => {
    estado.textContent = "Guardando la ubicación marcada en el mapa…";
    guardar(e.latlng.lat, e.latlng.lng, null, "manual");
  });
})();
