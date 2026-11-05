/*
 * cotizador.js — Cotización en vivo.
 *
 * Cada vez que el cliente cambia una opción:
 *   1. Arma la selección (solo identificadores, NUNCA precios).
 *   2. La manda al servidor (/api/cotizar/), que valida y calcula el precio.
 *   3. Muestra el desglose que respondió el servidor.
 *
 * Además emite el evento "seleccion-cambiada" con los colores y el estampado
 * elegidos, para que el simulador (simulador.js) redibuje el moño.
 */
(function () {
  const form = document.getElementById("form-cotizar");
  if (!form) return; // esta página no tiene cotizador

  const cuerpo = document.getElementById("cotizacion-cuerpo");
  const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value; // protección CSRF de Django
  const pesos = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
  let temporizador = null; // para esperar a que el cliente deje de mover opciones
  let ultimaPeticion = 0;  // para ignorar respuestas viejas

  // Campos que no son opciones del moño.
  const NO_SON_OPCIONES = ["csrfmiddlewaretoken", "cantidad", "estampado"];

  /** Lee el formulario y arma el JSON que se manda al servidor. */
  function leerSeleccion() {
    const datos = new FormData(form);
    const payload = {
      producto: form.dataset.producto,
      cantidad: Number(datos.get("cantidad")) || 1,
    };

    // Producto de catálogo: solo importa el SKU de la variante.
    if (datos.has("variante")) {
      payload.variante = datos.get("variante");
      return payload;
    }

    // Moño personalizable: id del color de cada parte + estampado opcional.
    payload.opciones = {};
    const colores = {};
    for (const [clave, valor] of datos.entries()) {
      if (NO_SON_OPCIONES.includes(clave)) continue;
      payload.opciones[clave] = Number(valor);
      const radio = form.querySelector(`input[name="${clave}"]:checked`);
      colores[clave] = radio ? radio.dataset.hex : null;
    }
    const estampado = datos.get("estampado") || null;
    if (estampado) payload.opciones.estampado = estampado;

    // Aviso para el simulador (no incluye precios).
    document.dispatchEvent(new CustomEvent("seleccion-cambiada", {
      detail: { colores, estampado },
    }));
    return payload;
  }

  /** Dibuja la tabla del desglose con formato de pesos mexicanos. */
  function pintarCotizacion(r) {
    const filas = r.conceptos
      .map((c) => `<tr><td>${c.descripcion}</td><td class="text-end">${pesos.format(c.importe)}</td></tr>`)
      .join("");
    const plural = r.dias_elaboracion === 1 ? "día" : "días";
    cuerpo.className = "small";
    cuerpo.innerHTML = `
      <table class="table table-sm mb-2"><tbody>${filas}
        <tr><td>Precio por pieza</td><td class="text-end">${pesos.format(r.precio_unitario)}</td></tr>
        <tr><td>Cantidad</td><td class="text-end">× ${r.cantidad}</td></tr>
        <tr class="fw-bold"><td>Total</td><td class="text-end">${pesos.format(r.total)}</td></tr>
      </tbody></table>
      <div class="text-body-secondary">${
        r.dias_elaboracion
          ? `Elaboración: ${r.dias_elaboracion} ${plural} hábiles + envío.`
          : "Listo para enviar."
      }</div>`;
  }

  function pintarError(mensaje) {
    cuerpo.className = "small text-danger";
    cuerpo.textContent = mensaje;
  }

  /** Pide la cotización al servidor. */
  async function cotizar() {
    const id = ++ultimaPeticion;
    try {
      const resp = await fetch(form.dataset.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify(leerSeleccion()),
      });
      const r = await resp.json();
      if (id !== ultimaPeticion) return; // llegó una respuesta vieja: se ignora
      r.ok ? pintarCotizacion(r) : pintarError(r.error);
    } catch (e) {
      if (id === ultimaPeticion) pintarError("No se pudo calcular la cotización. Intenta de nuevo.");
    }
  }

  /** Actualiza, en el título de cada parte, el nombre del color y el puntito de color. */
  function actualizarEtiquetas() {
    const estampado = form.querySelector('input[name="estampado"]:checked');
    const hayEstampado = estampado && estampado.value;

    form.querySelectorAll("[data-nombre-color]").forEach((el) => {
      const clave = el.dataset.nombreColor;
      const punto = form.querySelector(`[data-punto="${clave}"]`);
      const colores = form.querySelector(`[name="${clave}"]`)?.closest("[data-colores-estampable]");

      // El decorado con estampado muestra el nombre del estampado en lugar del color.
      if (hayEstampado && colores) {
        el.textContent = form.querySelector(`label[for="${estampado.id}"]`).title;
        if (punto) punto.style.background = `center / cover url("${form.querySelector(`label[for="${estampado.id}"] img`).src}")`;
        colores.classList.add("opacity-25");
        return;
      }
      if (colores) colores.classList.remove("opacity-25");

      const radio = form.querySelector(`input[name="${clave}"]:checked`);
      if (!radio) { el.textContent = ""; return; }
      el.textContent = form.querySelector(`label[for="${radio.id}"]`).title;
      if (punto) punto.style.background = radio.dataset.hex;
    });
  }

  // Cualquier cambio: actualiza etiquetas y cotiza 200 ms después del último cambio.
  form.addEventListener("input", (e) => {
    // Si el cliente toca un color del decorado mientras hay estampado, vuelve a "Liso".
    if (e.target.closest && e.target.closest("[data-colores-estampable]")) {
      const liso = form.querySelector('input[name="estampado"][value=""]');
      if (liso) liso.checked = true;
    }
    actualizarEtiquetas();
    clearTimeout(temporizador);
    temporizador = setTimeout(cotizar, 200);
  });

  actualizarEtiquetas();
  cotizar(); // primera cotización al cargar la página
})();
