/* Ovillito · comportamiento común (menús, carrito lateral, avisos, utilidades). */
(function () {
  "use strict";

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const csrf = () => ($('meta[name="csrf-token"]') || {}).content || "";

  /** Petición con CSRF que espera JSON. Lanza error si el servidor no responde JSON. */
  async function enviar(url, { metodo = "POST", datos = null, json = null } = {}) {
    const opciones = {
      method: metodo,
      credentials: "same-origin",
      headers: { "X-Requested-With": "fetch", "X-CSRFToken": csrf(), Accept: "application/json" },
    };
    if (json) {
      opciones.headers["Content-Type"] = "application/json";
      opciones.body = JSON.stringify(json);
    } else if (datos) {
      opciones.body = datos;
    }
    const respuesta = await fetch(url, opciones);
    const tipo = respuesta.headers.get("content-type") || "";
    if (!tipo.includes("application/json")) {
      // Normalmente significa que la sesión expiró y Django redirigió al login.
      if (respuesta.redirected) window.location.href = respuesta.url;
      throw new Error("El servidor no respondió como se esperaba. Recarga la página.");
    }
    return { ok: respuesta.ok, status: respuesta.status, datos: await respuesta.json() };
  }

  function icono(nombre, clase = "") {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", ("icono " + clase).trim());
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#i-" + nombre);
    svg.appendChild(use);
    return svg;
  }

  function toast(texto, nivel = "exito") {
    const zona = $("#toasts");
    if (!zona || !texto) return;
    const aviso = document.createElement("div");
    aviso.className = `mensaje mensaje--${nivel} toast`;
    aviso.appendChild(icono(nivel === "error" ? "cerrar" : nivel === "exito" ? "check" : "corazon"));
    const span = document.createElement("span");
    span.textContent = texto;
    aviso.appendChild(span);
    zona.appendChild(aviso);
    setTimeout(() => aviso.remove(), 3600);
  }

  function guardarPreferencia(clave, valor) {
    try { localStorage.setItem(clave, valor); } catch (e) { /* almacenamiento no disponible */ }
  }
  function leerPreferencia(clave) {
    try { return localStorage.getItem(clave); } catch (e) { return null; }
  }

  window.Ovillito = { $, $$, csrf, enviar, toast, icono };

  /* --- Menús desplegables --------------------------------------------------- */
  function cerrarDesplegables(excepto) {
    $$("[data-desplegar]").forEach((boton) => {
      const panel = document.getElementById(boton.dataset.desplegar);
      if (panel && panel !== excepto) {
        panel.dataset.abierto = "false";
        boton.setAttribute("aria-expanded", "false");
      }
    });
  }
  $$("[data-desplegar]").forEach((boton) => {
    boton.addEventListener("click", (e) => {
      e.stopPropagation();
      const panel = document.getElementById(boton.dataset.desplegar);
      const abrir = panel.dataset.abierto !== "true";
      cerrarDesplegables(panel);
      panel.dataset.abierto = String(abrir);
      boton.setAttribute("aria-expanded", String(abrir));
    });
  });

  /* --- Paneles alternables (menú móvil, buscador, barra lateral) ------------- */
  $$("[data-alternar]").forEach((boton) => {
    boton.addEventListener("click", (e) => {
      e.stopPropagation();
      const panel = document.getElementById(boton.dataset.alternar);
      if (!panel) return;
      const abrir = panel.dataset.abierto !== "true";
      panel.dataset.abierto = String(abrir);
      boton.setAttribute("aria-expanded", String(abrir));
      const veloPanel = $("[data-velo-panel]");
      if (veloPanel && boton.dataset.alternar === "lateral") veloPanel.dataset.abierto = String(abrir);
      if (abrir) {
        const campo = $("input", panel);
        if (campo && boton.dataset.alternar === "buscador") campo.focus();
      }
    });
  });
  function cerrarAlternables() {
    $$("[data-alternar]").forEach((boton) => {
      const panel = document.getElementById(boton.dataset.alternar);
      if (panel && panel.dataset.abierto === "true" && boton.dataset.alternar !== "buscador") {
        panel.dataset.abierto = "false";
        boton.setAttribute("aria-expanded", "false");
      }
    });
    const veloPanel = $("[data-velo-panel]");
    if (veloPanel) veloPanel.dataset.abierto = "false";
  }
  document.querySelectorAll("[data-cerrar-menu]").forEach((b) => b.addEventListener("click", (e) => {
    e.stopPropagation();
    cerrarAlternables();
  }));
  document.addEventListener("click", (e) => {
    if (!e.target.closest(".desplegable")) cerrarDesplegables();
    if (!e.target.closest(".nav__principal, .lateral, [data-alternar]")) cerrarAlternables();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { cerrarDesplegables(); cerrarAlternables(); }
  });

  /* --- Login: mostrar contraseña y cuentas de demostración ------------------- */
  $$("[data-ver-clave]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const campo = document.getElementById(boton.dataset.verClave);
      const visible = campo.type === "text";
      campo.type = visible ? "password" : "text";
      boton.setAttribute("aria-label", visible ? "Mostrar contraseña" : "Ocultar contraseña");
    });
  });
  $$("[data-demo]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const form = boton.closest("main").querySelector("form");
      form.querySelector('[name="username"]').value = boton.dataset.u;
      form.querySelector('[name="password"]').value = boton.dataset.p;
      const rol = form.querySelector(`[name="rol"][value="${boton.dataset.demo}"]`);
      if (rol) rol.checked = true;
      form.querySelector('[name="password"]').focus();
    });
  });

  /* --- Catálogo: filtros automáticos y densidad de la grilla ------------------ */
  $$("[data-autoenviar]").forEach((select) => {
    select.addEventListener("change", () => select.form.submit());
  });
  const grilla = $("[data-grilla]");
  if (grilla) {
    const botones = $$(".densidad [data-cols]");
    const aplicar = (cols) => {
      grilla.dataset.cols = cols;
      botones.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.cols === cols)));
    };
    const guardada = leerPreferencia("ovillito-columnas");
    if (guardada && ["2", "3", "4"].includes(guardada)) aplicar(guardada);
    botones.forEach((b) => b.addEventListener("click", () => {
      aplicar(b.dataset.cols);
      guardarPreferencia("ovillito-columnas", b.dataset.cols);
    }));
  }

  /* --- Selector de cantidad en el detalle de producto -------------------------- */
  $$("[data-selector-cantidad]").forEach((caja) => {
    const campo = $("input", caja);
    $$("[data-paso]", caja).forEach((b) => b.addEventListener("click", () => {
      const max = parseInt(campo.max || "99", 10);
      const valor = Math.min(max, Math.max(1, (parseInt(campo.value, 10) || 1) + parseInt(b.dataset.paso, 10)));
      campo.value = valor;
    }));
  });

  /* --- Panel: vista previa de colores del producto ------------------------------ */
  const campoColores = $("[data-colores]");
  const vistaColores = $("[data-vista-colores]");
  if (campoColores && vistaColores) {
    const pintar = () => {
      vistaColores.replaceChildren();
      campoColores.value.split(",").map((c) => c.trim()).filter((c) => /^#[0-9a-f]{6}$/i.test(c)).forEach((c) => {
        const punto = document.createElement("span");
        punto.style.background = c;
        punto.title = c;
        vistaColores.appendChild(punto);
      });
    };
    campoColores.addEventListener("input", pintar);
    pintar();
  }

  /* --- Carrito lateral ------------------------------------------------------- */
  const carrito = $("#carrito");
  if (!carrito) return;

  const velo = $("[data-velo]");
  const lista = $("[data-carrito-items]", carrito);
  const pie = $("[data-carrito-pie]", carrito);
  const nota = $("[data-carrito-nota]", carrito);
  const rutas = {
    api: carrito.dataset.api,
    agregar: carrito.dataset.urlAgregar,
    actualizar: carrito.dataset.urlActualizar,
    eliminar: carrito.dataset.urlEliminar,
    nota: carrito.dataset.urlNota,
  };
  const ruta = (plantilla, id) => plantilla.replace(/\/0\/$/, `/${id}/`);
  let ultimoFoco = null;

  function actualizarContadores(d) {
    $$("[data-contador-carrito]").forEach((c) => {
      c.textContent = d.cantidad;
      c.dataset.vacio = String(d.cantidad === 0);
    });
    $("[data-carrito-cantidad]", carrito).textContent = d.cantidad;
    $("[data-ver-carrito]", carrito).textContent = `Ver carrito (${d.cantidad})`;
    const pagar = $("[data-pagar]", carrito);
    pagar.textContent = d.cantidad ? `Pagar · ${d.subtotal_fmt}` : "Pagar";
    pagar.disabled = d.cantidad === 0;
  }

  function pintarEnvio(d) {
    const caja = $("[data-carrito-envio]", carrito);
    caja.replaceChildren();
    const texto = document.createElement("div");
    if (d.cantidad === 0) {
      texto.textContent = `Envío gratis en pedidos desde ${d.envio_gratis_fmt}`;
    } else if (d.falta_envio_gratis > 0) {
      texto.textContent = `Te faltan ${d.falta_fmt} para el envío gratis`;
    } else {
      texto.textContent = "¡Tu pedido tiene envío gratis!";
    }
    caja.appendChild(texto);
    if (d.cantidad > 0) {
      const barra = document.createElement("div");
      barra.className = "progreso";
      barra.setAttribute("role", "progressbar");
      barra.setAttribute("aria-label", "Progreso hacia el envío gratis");
      barra.setAttribute("aria-valuemin", "0");
      barra.setAttribute("aria-valuemax", "100");
      barra.setAttribute("aria-valuenow", String(d.progreso_envio));
      const relleno = document.createElement("span");
      relleno.style.width = d.progreso_envio + "%";
      barra.appendChild(relleno);
      caja.appendChild(barra);
    }
  }

  function crearItem(item) {
    const fila = document.createElement("div");
    fila.className = "item-carrito";
    fila.dataset.id = item.id;
    fila.dataset.cantidad = item.cantidad;

    const img = document.createElement("img");
    img.src = item.imagen;
    img.alt = "";
    fila.appendChild(img);

    const centro = document.createElement("div");
    const nombre = document.createElement("a");
    nombre.className = "item-carrito__nombre";
    nombre.href = item.url;
    nombre.textContent = item.nombre;
    const precio = document.createElement("div");
    precio.className = "item-carrito__precio";
    precio.textContent = item.precio_fmt;

    const controles = document.createElement("div");
    controles.className = "item-carrito__fila";
    const cantidad = document.createElement("div");
    cantidad.className = "cantidad";
    const menos = document.createElement("button");
    menos.type = "button";
    menos.dataset.accion = "menos";
    menos.setAttribute("aria-label", `Quitar una unidad de ${item.nombre}`);
    menos.appendChild(icono("menos", "icono--s"));
    const valor = document.createElement("output");
    valor.textContent = item.cantidad;
    valor.setAttribute("aria-label", "Cantidad");
    const mas = document.createElement("button");
    mas.type = "button";
    mas.dataset.accion = "mas";
    mas.setAttribute("aria-label", `Agregar una unidad de ${item.nombre}`);
    mas.appendChild(icono("mas", "icono--s"));
    mas.disabled = item.cantidad >= item.stock;
    cantidad.append(menos, valor, mas);
    const quitar = document.createElement("button");
    quitar.type = "button";
    quitar.className = "eliminar";
    quitar.dataset.accion = "eliminar";
    quitar.textContent = "Eliminar";
    controles.append(cantidad, quitar);
    centro.append(nombre, precio, controles);
    fila.appendChild(centro);

    const total = document.createElement("div");
    total.className = "item-carrito__total";
    total.textContent = item.subtotal_fmt;
    fila.appendChild(total);
    return fila;
  }

  function pintar(d) {
    actualizarContadores(d);
    pintarEnvio(d);
    lista.replaceChildren();
    if (d.items.length === 0) {
      const vacio = document.createElement("div");
      vacio.className = "carrito__vacio";
      const img = document.createElement("img");
      img.src = carrito.dataset.vacioImg;
      img.alt = "";
      const titulo = document.createElement("h3");
      titulo.textContent = "Tu carrito está vacío";
      const texto = document.createElement("p");
      texto.className = "texto-suave";
      texto.textContent = "Agrega un amigurumi y dale un hogar lleno de amor.";
      vacio.append(img, titulo, texto);
      lista.appendChild(vacio);
    } else {
      d.items.forEach((item) => lista.appendChild(crearItem(item)));
    }
    $$("details, [data-ver-carrito], [data-pagar], .carrito__legal", pie).forEach((el) => { el.hidden = d.items.length === 0; });
    if (document.activeElement !== nota) nota.value = d.nota || "";
  }

  async function cargar() {
    carrito.classList.add("cargando");
    try {
      const r = await fetch(rutas.api, { headers: { Accept: "application/json" }, credentials: "same-origin" });
      pintar(await r.json());
    } catch (e) {
      toast("No pudimos cargar tu carrito.", "error");
    } finally {
      carrito.classList.remove("cargando");
    }
  }

  function abrir() {
    ultimoFoco = document.activeElement;
    carrito.dataset.abierto = "true";
    carrito.removeAttribute("inert");
    carrito.setAttribute("aria-hidden", "false");
    velo.dataset.abierto = "true";
    document.body.style.overflow = "hidden";
    $(".cerrar", carrito).focus();
  }
  function cerrar() {
    carrito.dataset.abierto = "false";
    carrito.setAttribute("inert", "");
    carrito.setAttribute("aria-hidden", "true");
    velo.dataset.abierto = "false";
    document.body.style.overflow = "";
    if (ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
  }

  async function operar(url, datos, mensajeError = "No se pudo actualizar el carrito.") {
    carrito.classList.add("cargando");
    try {
      const r = await enviar(url, { datos });
      pintar(r.datos);
      if (r.datos.error) toast(r.datos.error, "error");
      return r.datos;
    } catch (e) {
      toast(e.message || mensajeError, "error");
      return null;
    } finally {
      carrito.classList.remove("cargando");
    }
  }

  async function agregar(id, cantidad = 1) {
    const datos = new FormData();
    datos.append("cantidad", cantidad);
    const r = await operar(ruta(rutas.agregar, id), datos);
    if (r && r.mensaje) toast(r.mensaje, r.nivel || "exito");
    if (r && !r.error) abrir();
  }

  document.addEventListener("click", (e) => {
    const botonAgregar = e.target.closest("[data-agregar]");
    if (botonAgregar) { e.preventDefault(); agregar(botonAgregar.dataset.agregar); return; }
    if (e.target.closest("[data-abrir-carrito]")) { e.preventDefault(); abrir(); cargar(); return; }
    if (e.target.closest("[data-cerrar-carrito]")) { e.preventDefault(); cerrar(); }
  });
  velo.addEventListener("click", cerrar);

  $$("[data-form-agregar]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const cantidad = parseInt((form.querySelector('[name="cantidad"]') || {}).value, 10) || 1;
      agregar(form.dataset.formAgregar, cantidad);
    });
  });

  lista.addEventListener("click", (e) => {
    const boton = e.target.closest("[data-accion]");
    if (!boton) return;
    const fila = boton.closest("[data-id]");
    const id = fila.dataset.id;
    const actual = parseInt(fila.dataset.cantidad, 10);
    if (boton.dataset.accion === "eliminar") {
      operar(ruta(rutas.eliminar, id), new FormData());
      return;
    }
    const datos = new FormData();
    datos.append("cantidad", boton.dataset.accion === "mas" ? actual + 1 : actual - 1);
    operar(ruta(rutas.actualizar, id), datos);
  });

  let temporizadorNota = null;
  nota.addEventListener("input", () => {
    clearTimeout(temporizadorNota);
    temporizadorNota = setTimeout(() => {
      const datos = new FormData();
      datos.append("nota", nota.value);
      enviar(rutas.nota, { datos }).catch(() => {});
    }, 600);
  });

  // Mantener el foco dentro del carrito mientras está abierto.
  carrito.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { cerrar(); return; }
    if (e.key !== "Tab") return;
    const enfocables = $$("a[href], button:not([disabled]), textarea, input, summary", carrito)
      .filter((el) => !el.closest("[hidden]") && el.offsetParent !== null);
    if (!enfocables.length) return;
    const primero = enfocables[0];
    const ultimo = enfocables[enfocables.length - 1];
    if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); ultimo.focus(); }
    else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primero.focus(); }
  });
})();
