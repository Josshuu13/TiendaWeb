/*
 * producto.js — Selección de color y talla en productos de catálogo
 * (suéteres, calcetines, moño escolar y kits).
 *
 *   - Dibuja un botón por color y uno por talla, a partir de las variantes que
 *     manda el servidor (config-variantes).
 *   - Las tallas agotadas en el color elegido salen tachadas y no se pueden elegir.
 *   - Guarda el SKU de la variante elegida en el campo oculto "variante" y avisa
 *     con un evento "input" para que cotizador.js recalcule el precio.
 *   - Cambia el color del dibujo o de la imagen del moño al elegir otro color.
 */
(function () {
  const datos = document.getElementById("config-variantes");
  const campo = document.getElementById("variante");
  if (!datos || !campo) return;

  const { colores, variantes } = JSON.parse(datos.textContent);
  const cajaColores = document.getElementById("colores");
  const cajaTallas = document.getElementById("tallas");
  const galeria = document.getElementById("galeria");
  let colorSel = null; // id del color elegido (null si el producto no tiene colores)
  let tallaSel = null; // clave de la talla elegida

  /** Variantes del color elegido (o todas, si el producto no maneja colores). */
  function delColor() {
    return variantes.filter((v) => colores.length === 0 || v.color === colorSel);
  }

  /** Cambia el color de la imagen: dibujo de prenda o vista del moño. */
  function pintarImagen() {
    const c = colores.find((x) => x.id === colorSel);
    if (!c || !galeria) return;
    galeria.querySelectorAll(".dibujo").forEach((svg) => svg.style.setProperty("--prenda", c.hex));
    galeria.querySelectorAll("img[data-base]").forEach((img) => { img.src = `${img.dataset.base}${c.slug}.webp`; });
  }

  /** Dibuja los botones de color. */
  function pintarColores() {
    document.getElementById("opcion-color").hidden = colores.length === 0;
    cajaColores.innerHTML = colores.map((c) => `
      <button type="button" class="color-boton ${c.id === colorSel ? "sel" : ""}" data-color="${c.id}"
              title="${c.nombre}" aria-label="${c.nombre}" aria-pressed="${c.id === colorSel}"
              style="background:${c.hex}"></button>`).join("");
    const c = colores.find((x) => x.id === colorSel);
    document.getElementById("color-nombre").textContent = c ? c.nombre : "";
  }

  /** Dibuja los botones de talla del color elegido. */
  function pintarTallas() {
    const lista = delColor();
    // Si solo hay "Unitalla", no hace falta mostrar el selector.
    document.getElementById("opcion-talla").hidden = lista.length <= 1 && (!lista[0] || lista[0].talla === "UNI");
    cajaTallas.innerHTML = lista.map((v) => {
      const agotada = v.existencias === 0;
      const extra = Number(v.precio_extra) > 0 ? ` (+$${Number(v.precio_extra).toFixed(0)})` : "";
      return `<button type="button" class="talla-boton ${v.talla === tallaSel ? "sel" : ""} ${agotada ? "agotada" : ""}"
                      data-talla="${v.talla}" ${agotada ? 'disabled title="Agotada"' : ""}>${v.talla_nombre}${extra}</button>`;
    }).join("");
    const v = lista.find((x) => x.talla === tallaSel);
    document.getElementById("talla-nombre").textContent = v
      ? v.talla_nombre + (v.existencias <= 3 ? ` · ¡últimas ${v.existencias}!` : "")
      : "elige una";
  }

  /** Guarda el SKU elegido y avisa para recotizar. */
  function actualizar() {
    const v = delColor().find((x) => x.talla === tallaSel && x.existencias > 0);
    campo.value = v ? v.sku : "";
    pintarColores();
    pintarTallas();
    pintarImagen();
    campo.dispatchEvent(new Event("input", { bubbles: true }));
  }

  /** Elige la primera talla con existencias del color actual. */
  function primeraTallaDisponible() {
    const v = delColor().find((x) => x.existencias > 0);
    tallaSel = v ? v.talla : null;
  }

  cajaColores.addEventListener("click", (e) => {
    const b = e.target.closest("[data-color]");
    if (!b) return;
    colorSel = Number(b.dataset.color);
    // Si la talla elegida no existe o está agotada en el nuevo color, se elige otra.
    if (!delColor().some((v) => v.talla === tallaSel && v.existencias > 0)) primeraTallaDisponible();
    actualizar();
  });

  cajaTallas.addEventListener("click", (e) => {
    const b = e.target.closest("[data-talla]");
    if (!b || b.disabled) return;
    tallaSel = b.dataset.talla;
    actualizar();
  });

  // Estado inicial: primer color con existencias y su primera talla disponible.
  const inicial = variantes.find((v) => v.existencias > 0) || variantes[0];
  colorSel = inicial && colores.length ? inicial.color : null;
  primeraTallaDisponible();
  actualizar();
})();
