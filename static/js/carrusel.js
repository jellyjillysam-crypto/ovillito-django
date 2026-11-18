/* Carrusel del home: autoplay, flechas, puntos, teclado, deslizamiento táctil y pausa. */
(function () {
  "use strict";
  const raiz = document.querySelector("[data-carrusel]");
  if (!raiz) return;
  const pista = raiz.querySelector("[data-pista]");
  const slides = Array.from(pista.children);
  if (slides.length < 2) return;

  const puntos = Array.from(raiz.querySelectorAll("[data-ir]"));
  const botonPausa = raiz.querySelector("[data-pausa]");
  const reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const INTERVALO = 5500;
  let actual = 0;
  let temporizador = null;
  let pausadoPorUsuario = reducirMovimiento;

  function ir(indice) {
    actual = (indice + slides.length) % slides.length;
    pista.style.transform = `translateX(-${actual * 100}%)`;
    slides.forEach((slide, i) => {
      const activa = i === actual;
      slide.classList.toggle("es-activa", activa);
      slide.setAttribute("aria-hidden", String(!activa));
      slide.querySelectorAll("a, button").forEach((el) => { el.tabIndex = activa ? 0 : -1; });
    });
    puntos.forEach((p, i) => p.setAttribute("aria-current", String(i === actual)));
  }

  function detener() { clearInterval(temporizador); temporizador = null; }
  function iniciar() {
    detener();
    if (!pausadoPorUsuario) temporizador = setInterval(() => ir(actual + 1), INTERVALO);
  }

  function pintarPausa() {
    if (!botonPausa) return;
    botonPausa.setAttribute("aria-label", pausadoPorUsuario ? "Reanudar carrusel" : "Pausar carrusel");
    const use = botonPausa.querySelector("use");
    if (use) use.setAttribute("href", pausadoPorUsuario ? "#i-play" : "#i-pausa");
  }

  raiz.querySelector("[data-prev]").addEventListener("click", () => { ir(actual - 1); iniciar(); });
  raiz.querySelector("[data-next]").addEventListener("click", () => { ir(actual + 1); iniciar(); });
  puntos.forEach((p) => p.addEventListener("click", () => { ir(parseInt(p.dataset.ir, 10)); iniciar(); }));
  if (botonPausa) {
    botonPausa.addEventListener("click", () => {
      pausadoPorUsuario = !pausadoPorUsuario;
      pintarPausa();
      iniciar();
    });
  }

  raiz.addEventListener("mouseenter", detener);
  raiz.addEventListener("mouseleave", iniciar);
  raiz.addEventListener("focusin", detener);
  raiz.addEventListener("focusout", (e) => { if (!raiz.contains(e.relatedTarget)) iniciar(); });
  raiz.addEventListener("keydown", (e) => {
    if (e.key === "ArrowLeft") { ir(actual - 1); }
    if (e.key === "ArrowRight") { ir(actual + 1); }
  });

  // Deslizar con el dedo en pantallas táctiles.
  let inicioX = null;
  raiz.addEventListener("pointerdown", (e) => { if (e.pointerType !== "mouse") inicioX = e.clientX; });
  raiz.addEventListener("pointerup", (e) => {
    if (inicioX === null) return;
    const delta = e.clientX - inicioX;
    if (Math.abs(delta) > 40) { ir(actual + (delta < 0 ? 1 : -1)); iniciar(); }
    inicioX = null;
  });

  document.addEventListener("visibilitychange", () => (document.hidden ? detener() : iniciar()));

  ir(0);
  pintarPausa();
  iniciar();
})();
