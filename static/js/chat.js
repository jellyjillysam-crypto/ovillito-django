/* Chat de la comunidad: envío de mensajes y actualización periódica (polling). */
(function () {
  "use strict";
  const { $, enviar, toast } = window.Ovillito;
  const raiz = $("[data-chat]");
  if (!raiz) return;
  const lista = $("[data-lista]", raiz);
  const form = $("[data-form-chat]", raiz);
  const campo = $("input", form);
  const esAdmin = raiz.dataset.admin === "1";
  const INTERVALO = 3000;
  let ultimoId = 0;
  let ultimoDia = null;
  let consultando = false;

  const cercaDelFinal = () => lista.scrollHeight - lista.scrollTop - lista.clientHeight < 120;
  const bajar = () => { lista.scrollTop = lista.scrollHeight; };

  function crearBurbuja(m) {
    const fila = document.createElement("div");
    fila.className = "burbuja-chat" + (m.es_mio ? " burbuja-chat--mia" : "") + (m.es_admin ? " burbuja-chat--admin" : "");
    fila.dataset.id = m.id;

    const avatar = document.createElement("span");
    avatar.className = "burbuja-chat__avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = m.inicial;

    const cuerpo = document.createElement("div");
    cuerpo.className = "burbuja-chat__cuerpo";
    const autor = document.createElement("div");
    autor.className = "burbuja-chat__autor";
    autor.textContent = m.es_mio ? "Tú" : m.autor;
    if (m.es_admin) {
      const insignia = document.createElement("span");
      insignia.className = "insignia insignia--verde";
      insignia.textContent = "Equipo";
      autor.appendChild(insignia);
    }
    const texto = document.createElement("p");
    texto.className = "burbuja-chat__texto";
    texto.textContent = m.texto;
    const hora = document.createElement("span");
    hora.className = "burbuja-chat__hora";
    hora.textContent = m.hora;
    cuerpo.append(autor, texto, hora);

    if (esAdmin) {
      const borrar = document.createElement("button");
      borrar.type = "button";
      borrar.className = "burbuja-chat__borrar";
      borrar.textContent = "Eliminar";
      borrar.setAttribute("aria-label", `Eliminar mensaje de ${m.autor}`);
      borrar.addEventListener("click", async () => {
        const url = raiz.dataset.urlEliminar.replace(/\/0\/eliminar\/$/, `/${m.id}/eliminar/`);
        try {
          const r = await enviar(url);
          if (r.ok) fila.remove();
        } catch (e) { toast(e.message, "error"); }
      });
      hora.after(borrar);
    }
    fila.append(avatar, cuerpo);
    return fila;
  }

  function agregar(m) {
    if (lista.querySelector(`[data-id="${m.id}"]`)) return;
    if (m.dia !== ultimoDia) {
      const sep = document.createElement("div");
      sep.className = "separador-dia";
      sep.textContent = m.dia;
      lista.appendChild(sep);
      ultimoDia = m.dia;
    }
    lista.appendChild(crearBurbuja(m));
    ultimoId = Math.max(ultimoId, m.id);
  }

  function vacio() {
    if (lista.children.length) return;
    const aviso = document.createElement("p");
    aviso.className = "separador-dia";
    aviso.dataset.vacio = "";
    aviso.textContent = "Aún no hay mensajes. ¡Saluda a la comunidad!";
    lista.appendChild(aviso);
  }

  async function consultar() {
    if (consultando || document.hidden) return;
    consultando = true;
    try {
      const r = await fetch(`${raiz.dataset.urlMensajes}?despues=${ultimoId}`, {
        headers: { Accept: "application/json" }, credentials: "same-origin",
      });
      if (!r.ok) return;
      const { mensajes } = await r.json();
      if (mensajes.length) {
        const pegado = cercaDelFinal();
        const aviso = lista.querySelector("[data-vacio]");
        if (aviso) aviso.remove();
        mensajes.forEach(agregar);
        if (pegado) bajar();
      }
    } catch (e) {
      /* sin conexión momentánea: se reintenta en el siguiente ciclo */
    } finally {
      consultando = false;
    }
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const texto = campo.value.trim();
    if (!texto) return;
    campo.disabled = true;
    try {
      const r = await enviar(raiz.dataset.urlEnviar, { json: { texto } });
      if (!r.ok) throw new Error(r.datos.error || "No se pudo enviar el mensaje.");
      const aviso = lista.querySelector("[data-vacio]");
      if (aviso) aviso.remove();
      agregar(r.datos.mensaje);
      campo.value = "";
      bajar();
    } catch (err) {
      toast(err.message, "error");
    } finally {
      campo.disabled = false;
      campo.focus();
    }
  });

  JSON.parse(document.getElementById("mensajes-iniciales").textContent).forEach(agregar);
  vacio();
  bajar();
  setInterval(consultar, INTERVALO);
})();
