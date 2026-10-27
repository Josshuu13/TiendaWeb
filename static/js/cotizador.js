/*
 * Cotizador: cada vez que el cliente cambia una opción, manda la selección al
 * servidor (/api/cotizar/) y muestra el desglose que el servidor calcula.
 * El navegador NUNCA calcula ni envía precios.
 *
 * También emite el evento "seleccion-cambiada" con los colores elegidos, para que
 * el simulador (canvas con fotos) se redibuje sin depender de este archivo.
 */
(function () {
  const form = document.getElementById("form-cotizar");
  if (!form) return;

  const cuerpo = document.getElementById("cotizacion-cuerpo");
  const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
  const pesos = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
  let temporizador = null;
  let ultimaPeticion = 0;

  function leerSeleccion() {
    const datos = new FormData(form);
    const payload = {
      producto: form.dataset.producto,
      cantidad: Number(datos.get("cantidad")) || 1,
    };
    if (datos.has("variante")) {
      payload.variante = datos.get("variante");
    } else {
      payload.opciones = {};
      const colores = {};
      for (const [clave, valor] of datos.entries()) {
        if (["csrfmiddlewaretoken", "cantidad"].includes(clave)) continue;
        if (clave === "decoracion") {
          if (valor) payload.opciones.decoracion = valor;
          continue;
        }
        payload.opciones[clave] = Number(valor);
        const radio = form.querySelector(`input[name="${clave}"]:checked`);
        colores[clave] = radio ? radio.dataset.hex : null;
      }
      document.dispatchEvent(new CustomEvent("seleccion-cambiada", {
        detail: { colores, decoracion: payload.opciones.decoracion || null },
      }));
    }
    return payload;
  }

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

  async function cotizar() {
    const id = ++ultimaPeticion;
    try {
      const resp = await fetch(form.dataset.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
        body: JSON.stringify(leerSeleccion()),
      });
      const r = await resp.json();
      if (id !== ultimaPeticion) return; // llegó una respuesta vieja
      r.ok ? pintarCotizacion(r) : pintarError(r.error);
    } catch (e) {
      if (id === ultimaPeticion) pintarError("No se pudo calcular la cotización. Intenta de nuevo.");
    }
  }

  function actualizarNombresColor() {
    form.querySelectorAll("[data-nombre-color]").forEach((el) => {
      const clave = el.dataset.nombreColor;
      const radio = form.querySelector(`input[name="${clave}"]:checked`);
      el.textContent = radio ? form.querySelector(`label[for="${radio.id}"]`).title : "";
    });
  }

  form.addEventListener("input", () => {
    actualizarNombresColor();
    clearTimeout(temporizador);
    temporizador = setTimeout(cotizar, 200);
  });

  // Vista provisional (se reemplaza por el simulador real)
  document.addEventListener("seleccion-cambiada", (e) => {
    for (const [clave, hex] of Object.entries(e.detail.colores)) {
      const punto = document.querySelector(`[data-muestra="${clave}"]`);
      if (punto && hex) punto.style.background = hex;
    }
  });

  actualizarNombresColor();
  cotizar();
})();
