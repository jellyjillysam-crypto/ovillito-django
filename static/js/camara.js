/* Toma de fotos con la cámara (getUserMedia) y subida a la galería. */
(function () {
  "use strict";
  const { $, $$, enviar, toast } = window.Ovillito;
  const app = $("[data-camara-app]");
  if (!app) return;

  const video = $("[data-video]", app);
  const lienzo = $("[data-lienzo]", app);
  const aviso = $("[data-aviso]", app);
  const flash = $("[data-flash]", app);
  const bActivar = $("[data-activar]", app);
  const bCapturar = $("[data-capturar]", app);
  const bCambiar = $("[data-cambiar]", app);
  const bRepetir = $("[data-repetir]", app);
  const form = $("[data-form-foto]", app);
  const archivo = $("[data-archivo]", form);
  const estado = $("[data-estado-foto]", form);
  const galeria = $("[data-galeria]");
  const galeriaVacia = $("[data-galeria-vacia]");
  const total = $("[data-total-fotos]");

  let flujo = null;
  let modo = "environment";
  let fotoCapturada = null;
  let vistaPrevia = null;

  function mensaje(texto) { estado.textContent = texto; }

  function detener() {
    if (flujo) flujo.getTracks().forEach((t) => t.stop());
    flujo = null;
  }

  async function activar() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      mensaje("Tu navegador no permite usar la cámara aquí. Usa la opción de subir una foto.");
      return;
    }
    if (!window.isSecureContext) {
      mensaje("La cámara solo funciona en https:// o en localhost. Usa la opción de subir una foto.");
      return;
    }
    detener();
    bActivar.disabled = true;
    mensaje("Solicitando permiso para usar la cámara…");
    try {
      flujo = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: modo, width: { ideal: 1280 }, height: { ideal: 960 } },
        audio: false,
      });
      video.srcObject = flujo;
      await video.play();
      video.hidden = false;
      lienzo.hidden = true;
      aviso.hidden = true;
      bCapturar.disabled = false;
      bRepetir.hidden = true;
      fotoCapturada = null;
      mensaje("Cámara lista. Encuadra tu tejido y pulsa «Tomar foto».");
      const dispositivos = await navigator.mediaDevices.enumerateDevices();
      bCambiar.hidden = dispositivos.filter((d) => d.kind === "videoinput").length < 2;
      bActivar.textContent = "Reiniciar cámara";
    } catch (e) {
      const errores = {
        NotAllowedError: "No diste permiso para usar la cámara. Revísalo en la configuración del navegador.",
        NotFoundError: "No encontramos ninguna cámara en este dispositivo.",
        NotReadableError: "La cámara está siendo usada por otra aplicación.",
      };
      mensaje(errores[e.name] || "No se pudo iniciar la cámara.");
    } finally {
      bActivar.disabled = false;
    }
  }

  function capturar() {
    if (!flujo || !video.videoWidth) return;
    lienzo.width = video.videoWidth;
    lienzo.height = video.videoHeight;
    lienzo.getContext("2d").drawImage(video, 0, 0, lienzo.width, lienzo.height);
    flash.classList.remove("activo");
    void flash.offsetWidth; // reinicia la animación del destello
    flash.classList.add("activo");
    lienzo.toBlob((blob) => {
      fotoCapturada = blob;
      lienzo.hidden = false;
      video.hidden = true;
      bCapturar.disabled = true;
      bRepetir.hidden = false;
      archivo.value = "";
      mensaje("¡Foto lista! Agrega una descripción y pulsa «Guardar foto».");
    }, "image/jpeg", 0.88);
  }

  function repetir() {
    fotoCapturada = null;
    lienzo.hidden = true;
    video.hidden = !flujo;
    bCapturar.disabled = !flujo;
    bRepetir.hidden = true;
    mensaje("");
  }

  function mostrarArchivo() {
    const f = archivo.files[0];
    if (!f) return;
    fotoCapturada = null;
    if (vistaPrevia) URL.revokeObjectURL(vistaPrevia);
    vistaPrevia = URL.createObjectURL(f);
    let img = $(".camara img.vista-archivo", app);
    if (!img) {
      img = document.createElement("img");
      img.className = "vista-archivo";
      img.alt = "Vista previa de la foto elegida";
      $(".camara", app).appendChild(img);
    }
    img.src = vistaPrevia;
    aviso.hidden = true;
    video.hidden = true;
    lienzo.hidden = true;
    mensaje("Foto elegida. Pulsa «Guardar foto» para subirla.");
  }

  function crearFigura(foto) {
    const figura = document.createElement("figure");
    figura.className = "foto";
    figura.dataset.foto = foto.id;
    const img = document.createElement("img");
    img.src = foto.url;
    img.alt = foto.descripcion || "Foto de tejido";
    const pie = document.createElement("figcaption");
    if (foto.descripcion) {
      const titulo = document.createElement("strong");
      titulo.textContent = foto.descripcion;
      pie.appendChild(titulo);
    }
    const fila = document.createElement("div");
    fila.className = "foto__pie";
    const fecha = document.createElement("span");
    fecha.className = "texto-mini";
    fecha.textContent = foto.fecha;
    fila.appendChild(fecha);
    if (foto.puede_eliminar) {
      const f = document.createElement("form");
      f.method = "post";
      f.action = app.dataset.urlEliminar.replace(/\/0\/eliminar\/$/, `/${foto.id}/eliminar/`);
      f.dataset.eliminarFoto = "";
      const b = document.createElement("button");
      b.className = "eliminar";
      b.type = "submit";
      b.textContent = "Eliminar";
      f.appendChild(b);
      fila.appendChild(f);
    }
    pie.appendChild(fila);
    figura.append(img, pie);
    return figura;
  }

  function actualizarTotal() {
    const n = galeria.children.length;
    total.textContent = `${n} foto${n === 1 ? "" : "s"}`;
    galeriaVacia.hidden = n > 0;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const datos = new FormData(form);
    const elegido = archivo.files[0];
    if (fotoCapturada) {
      datos.set("imagen", fotoCapturada, `foto-${Date.now()}.jpg`);
    } else if (!elegido) {
      mensaje("Primero toma una foto con la cámara o elige una imagen.");
      return;
    }
    const boton = $("[data-guardar]", form);
    boton.disabled = true;
    mensaje("Subiendo foto…");
    try {
      const r = await enviar(app.dataset.urlSubir, { datos });
      if (!r.ok) throw new Error(r.datos.error || "No se pudo guardar la foto.");
      galeria.prepend(crearFigura(r.datos.foto));
      actualizarTotal();
      form.reset();
      repetir();
      const previa = $(".camara img.vista-archivo", app);
      if (previa) previa.remove();
      if (!flujo) aviso.hidden = false;
      mensaje("¡Foto guardada en la galería!");
      toast("¡Foto guardada!");
    } catch (err) {
      mensaje(err.message);
      toast(err.message, "error");
    } finally {
      boton.disabled = false;
    }
  });

  document.addEventListener("submit", async (e) => {
    const f = e.target.closest("[data-eliminar-foto]");
    if (!f) return;
    e.preventDefault();
    if (!window.confirm("¿Eliminar esta foto?")) return;
    try {
      const r = await enviar(f.action);
      if (r.ok) {
        f.closest("[data-foto]").remove();
        actualizarTotal();
        toast("Foto eliminada.", "info");
      }
    } catch (err) {
      toast(err.message, "error");
    }
  });

  bActivar.addEventListener("click", activar);
  bCapturar.addEventListener("click", capturar);
  bRepetir.addEventListener("click", repetir);
  bCambiar.addEventListener("click", () => { modo = modo === "environment" ? "user" : "environment"; activar(); });
  archivo.addEventListener("change", mostrarArchivo);
  window.addEventListener("pagehide", detener);
})();
