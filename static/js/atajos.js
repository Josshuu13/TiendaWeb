/*
 * atajos.js — Barra "Categorías:" de la página de Moños.
 *
 * Los botones ya funcionan sin este archivo (son enlaces a #navideno, #uniforme...).
 * Aquí solo se marca el botón de la sección que se está viendo y, en celular,
 * se recorre la fila para que ese botón quede a la vista.
 */
(function () {
  const barra = document.querySelector("[data-atajos]");
  if (!barra || !("IntersectionObserver" in window)) return;

  const enlaces = [...barra.querySelectorAll('a[href^="#"]')];
  const secciones = enlaces.map((a) => document.querySelector(a.getAttribute("href"))).filter(Boolean);

  /** Marca el botón de la sección con id `id`. */
  function marcar(id) {
    enlaces.forEach((a) => {
      const activa = a.getAttribute("href") === `#${id}`;
      a.classList.toggle("activa", activa);
      if (activa) {
        a.setAttribute("aria-current", "true");
        // En celular la fila se desliza para mostrar el botón activo.
        barra.scrollTo({ left: a.offsetLeft - 16, behavior: "smooth" });
      } else {
        a.removeAttribute("aria-current");
      }
    });
  }

  // La sección "activa" es la que cruza una franja cerca de la parte de arriba de la pantalla.
  const observador = new IntersectionObserver(
    (entradas) => entradas.forEach((e) => { if (e.isIntersecting) marcar(e.target.id); }),
    { rootMargin: "-30% 0px -60% 0px" },
  );
  secciones.forEach((s) => observador.observe(s));
})();
