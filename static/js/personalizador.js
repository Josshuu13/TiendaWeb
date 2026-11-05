/*
 * personalizador.js — Personalización del moño paso a paso.
 *
 *   - Muestra una parte a la vez (Patas → Base superior → ... → Nudo).
 *   - Botones "← Anterior" y "Siguiente: ... →"; también se puede saltar a
 *     cualquier parte haciendo clic en su círculo.
 *   - Marca con ✓ las partes que el cliente ya visitó.
 *   - Avisa al simulador qué parte se está eligiendo (evento "parte-activa"),
 *     para que la resalte un momento en el moño.
 *   - "↺ Restablecer": regresa todos los colores a los iniciales y al paso 1.
 *   - "★ Lo más vendido": aplica una combinación lista de colores.
 *
 * Este archivo NO calcula precios ni dibuja: solo cambia los botones de opción
 * del formulario y avisa con un evento "input"; cotizador.js y simulador.js
 * reaccionan a ese aviso.
 */
(function () {
  const raiz = document.getElementById("personalizador");
  const form = document.getElementById("form-cotizar");
  if (!raiz || !form) return; // esta página no tiene personalizador

  const total = Number(raiz.dataset.total);
  const botones = [...raiz.querySelectorAll(".parte-boton")];
  const paneles = [...raiz.querySelectorAll(".parte-panel")];
  const textoPaso = document.getElementById("paso-texto");
  const visitados = new Set([1]); // pasos que el cliente ya vio
  let paso = 1;

  /** Avisa a cotizador.js y simulador.js que cambió la selección. */
  function avisarCambio() {
    form.dispatchEvent(new Event("input", { bubbles: true }));
  }

  /** Cambia al paso indicado (1 a total) y actualiza botones y paneles. */
  function irAPaso(nuevo, resaltar = true) {
    paso = Math.min(total, Math.max(1, nuevo));
    visitados.add(paso);

    botones.forEach((b) => {
      const n = Number(b.dataset.paso);
      const activa = n === paso;
      b.classList.toggle("activa", activa);
      b.classList.toggle("hecha", visitados.has(n) && !activa);
      b.setAttribute("aria-selected", activa ? "true" : "false");
    });
    paneles.forEach((p) => { p.hidden = Number(p.dataset.panel) !== paso; });

    const actual = botones[paso - 1];
    textoPaso.textContent = `Paso ${paso} de ${total} · ${actual.dataset.nombre}`;

    // El simulador resalta en el moño la parte que se está eligiendo.
    if (resaltar) {
      document.dispatchEvent(new CustomEvent("parte-activa", {
        detail: { clave: actual.dataset.clave, nombre: actual.dataset.nombre },
      }));
    }
  }

  // Clic en un círculo de la fila de partes: saltar a esa parte.
  botones.forEach((b) => b.addEventListener("click", () => irAPaso(Number(b.dataset.paso))));

  // Botones "Anterior", "Siguiente" y "Listo" de cada panel.
  raiz.addEventListener("click", (e) => {
    const boton = e.target.closest("[data-ir]");
    if (!boton) return;
    const accion = boton.dataset.ir;
    if (accion === "anterior") irAPaso(paso - 1);
    else if (accion === "siguiente") irAPaso(paso + 1);
    else if (accion === "listo") {
      document.getElementById("cotizacion")?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });

  // ↺ Restablecer: colores iniciales, decorado liso y regreso al paso 1.
  document.getElementById("btn-restablecer")?.addEventListener("click", () => {
    form.querySelectorAll("input[data-inicial]").forEach((r) => { r.checked = true; });
    const liso = form.querySelector('input[name="estampado"][value=""]');
    if (liso) liso.checked = true;
    visitados.clear();
    visitados.add(1);
    avisarCambio();
    irAPaso(1);
  });

  // ★ Lo más vendido: mostrar/ocultar la lista y aplicar una combinación.
  const btnVendido = document.getElementById("btn-vendido");
  const listaVendidos = document.getElementById("vendidos");
  const datosCombos = document.getElementById("config-combinaciones");
  const combinaciones = datosCombos ? JSON.parse(datosCombos.textContent) : [];

  btnVendido?.addEventListener("click", () => {
    listaVendidos.hidden = !listaVendidos.hidden;
    btnVendido.setAttribute("aria-expanded", String(!listaVendidos.hidden));
  });

  raiz.querySelectorAll("[data-combo]").forEach((boton) => {
    boton.addEventListener("click", () => {
      const combo = combinaciones[Number(boton.dataset.combo)];
      if (!combo) return;
      // Marcar el color de cada parte.
      for (const [clave, idColor] of Object.entries(combo.colores)) {
        const radio = form.querySelector(`input[name="${clave}"][value="${idColor}"]`);
        if (radio) radio.checked = true;
      }
      // Estampado de la combinación (o liso si no tiene).
      const est = form.querySelector(`input[name="estampado"][value="${combo.estampado || ""}"]`);
      if (est) est.checked = true;

      listaVendidos.hidden = true;
      btnVendido.setAttribute("aria-expanded", "false");
      avisarCambio();
    });
  });

  irAPaso(1, false); // estado inicial (sin resaltar al cargar la página)
})();
