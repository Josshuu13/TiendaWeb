/*
 * decorado.js — Paso "Decorado" del moño: liso o listón estampado.
 *
 *   - "Liso" / "Estampado": dos opciones arriba. Con "Estampado" se muestran los
 *     diseños (puntas de listón) agrupados en Escolares, Navideños y Otros, y se
 *     oculta la paleta de colores lisos.
 *   - Al tocar un diseño se elige su primer color y, si tiene varios, se abre
 *     abajo la fila de circulitos con sus colores.
 *   - La punta del diseño elegido toma la foto del color elegido.
 *
 * Igual que personalizador.js, este archivo solo cambia los botones de opción del
 * formulario y avisa con un evento "input"; cotizador.js y simulador.js reaccionan.
 */
(function () {
  const form = document.getElementById("form-cotizar");
  const contenedor = document.querySelector("[data-estampados]");
  if (!form || !contenedor) return; // esta página no tiene estampados

  const botonEstampado = document.querySelector("[data-ver-estampados]");
  const etiquetaLiso = document.querySelector('label[for="est-liso"]');
  const paletaLisa = form.querySelector("[data-colores-estampable]");
  let abierto = false; // el cliente tocó "Estampado" aunque todavía no elija diseño

  /** Pone la página de acuerdo con el estampado elegido. */
  function sincronizar() {
    const elegido = form.querySelector('input[name="estampado"]:checked');
    const hayEstampado = Boolean(elegido && elegido.value);
    if (!hayEstampado && elegido) abierto = false; // eligió "Liso"
    const mostrar = hayEstampado || abierto;

    contenedor.hidden = !mostrar;
    if (paletaLisa) paletaLisa.hidden = hayEstampado;
    botonEstampado.classList.toggle("activa", mostrar);
    botonEstampado.setAttribute("aria-expanded", String(mostrar));
    etiquetaLiso.classList.toggle("activa", !mostrar);

    const diseno = hayEstampado ? elegido.dataset.diseno : null;
    // Marca la punta del diseño elegido y le pone la foto del color elegido.
    contenedor.querySelectorAll(".diseno").forEach((punta) => {
      const esEste = punta.dataset.diseno === diseno;
      punta.classList.toggle("sel", esEste);
      if (esEste) punta.querySelector("[data-portada]").src = elegido.dataset.img;
    });
    // Abre los colores del diseño elegido (solo si tiene más de uno).
    contenedor.querySelectorAll("[data-colores-de]").forEach((fila) => {
      const esEste = fila.dataset.coloresDe === diseno;
      fila.hidden = !(esEste && fila.querySelector(".muestra"));
      const titulo = fila.querySelector("[data-color-elegido]");
      if (esEste && titulo) titulo.textContent = elegido.dataset.color;
    });
  }

  // "Estampado": muestra los diseños y, si no había uno elegido, pone el primero
  // para que el cliente vea de inmediato un listón estampado en el moño.
  botonEstampado.addEventListener("click", () => {
    abierto = true;
    const elegido = form.querySelector('input[name="estampado"]:checked');
    if (!elegido || !elegido.value) {
      const primero = contenedor.querySelector('input[name="estampado"]');
      if (primero) primero.checked = true;
      form.dispatchEvent(new Event("input", { bubbles: true }));
    }
    sincronizar();
  });

  // Cualquier cambio del formulario (también "Restablecer" y "Lo más vendido").
  form.addEventListener("input", sincronizar);
  form.addEventListener("change", sincronizar);
  sincronizar();
})();
