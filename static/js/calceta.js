/*
 * calceta.js — Personalizador de calcetas con capas de un render realista.
 *
 * Cómo funciona (igual que el simulador del moño):
 *   - Una calceta de tejido blanca, acostada y vista desde arriba, se hizo en Blender con
 *     la silueta de los calcetines del catálogo, puntadas, resorte en el puño, pliegues y
 *     luz de estudio. El render se separó en capas PNG en escala de grises:
 *       sombra.png    la sombra en el piso
 *       cuerpo.png    el cuerpo de la calceta
 *       detalles.png  puño, talón y punta
 *     El gris guarda la luz, las sombras y el tejido; el color se pone aquí.
 *   - Para pintar una capa se usa la fusión "multiply": lo claro queda del color elegido
 *     y las sombras quedan del mismo color, pero más oscuro. Así se ve la tela.
 *   - El diseño se estampa en la pierna y luego se multiplica por la capa del cuerpo,
 *     para que tome las puntadas, los pliegues y la luz.
 *   - Las fuentes para volver a generar las capas están en docs/simulador-calceta/.
 *
 * No calcula precios: solo lee el formulario. cotizador.js manda la selección al
 * servidor, que valida cada valor.
 */
(function () {
  const canvas = document.getElementById("calceta");
  const datos = document.getElementById("config-calceta");
  const form = document.getElementById("form-cotizar");
  if (!canvas || !datos || !form) return; // esta página no tiene personalizador de calcetas

  const config = JSON.parse(datos.textContent);
  const ctx = canvas.getContext("2d");
  const ANCHO = 720, ALTO = 900;
  const ZONA = { x0: 330, x1: 500, y0: 240, y1: 540 }; // dónde puede quedar el centro del diseño
  const TAMANO_BASE = 150;                               // lado del diseño al 100 %

  const capas = {};               // nombre -> <img> de la capa
  const cacheColor = new Map();   // "capa|#hex" -> canvas ya pintado
  const imagenes = {};            // clave del diseño -> <img>
  let listo = false;              // true cuando cargaron todas las capas
  const ajustes = document.getElementById("calceta-ajustes");

  // ------------------------------------------------------------ utilidades
  function cargarImagen(url) {
    return new Promise((resolver, rechazar) => {
      const img = new Image();
      img.onload = () => resolver(img);
      img.onerror = () => rechazar(new Error("No se pudo cargar " + url));
      img.src = url;
    });
  }

  function lienzo(ancho = ANCHO, alto = ALTO) {
    const c = document.createElement("canvas");
    c.width = ancho;
    c.height = alto;
    return c;
  }

  // -------------------------------------------------------- leer el formulario
  function colorDe(clave) {
    const radio = form.querySelector(`input[name="${clave}"]:checked`);
    return radio ? radio.dataset.hex : "#cccccc";
  }

  function disenoElegido() {
    const radio = form.querySelector('input[name="diseno"]:checked');
    return radio ? radio.value : "";
  }

  function leer() {
    const [cuerpo, detalles] = config.partes;
    return {
      cuerpo: colorDe(cuerpo),
      detalles: colorDe(detalles || cuerpo),
      diseno: disenoElegido(),
      x: Number(form.elements.x.value),
      y: Number(form.elements.y.value),
      tamano: Number(form.elements.tamano.value),
    };
  }

  /** Devuelve la imagen del diseño si ya cargó; si no, la pide y redibuja al llegar. */
  function imagenDe(clave) {
    if (!clave || !config.disenos[clave]) return null;
    if (!imagenes[clave]) {
      const img = new Image();
      img.onload = dibujar;
      img.src = config.disenos[clave];
      imagenes[clave] = img;
    }
    const img = imagenes[clave];
    return img.complete && img.naturalWidth ? img : null;
  }

  // ------------------------------------------------------------ pintar capas
  /** Capa teñida de un color (fusión multiply), con caché. */
  function capaColor(nombre, hex) {
    const llave = nombre + "|" + hex;
    if (cacheColor.has(llave)) return cacheColor.get(llave);
    const c = lienzo();
    const g = c.getContext("2d");
    g.drawImage(capas[nombre], 0, 0);          // 1) foto gris de la capa
    g.globalCompositeOperation = "multiply";
    g.fillStyle = hex;
    g.fillRect(0, 0, ANCHO, ALTO);             // 2) multiplica por el color
    g.globalCompositeOperation = "destination-in";
    g.drawImage(capas[nombre], 0, 0);          // 3) recorta a la forma de la capa
    cacheColor.set(llave, c);
    return c;
  }

  /** El diseño estampado en la pierna: toma el tejido, la luz y los pliegues del render. */
  function capaDiseno(sel) {
    const img = imagenDe(sel.diseno);
    if (!img) return null;
    const lado = Math.round((TAMANO_BASE * sel.tamano) / 100);
    const cx = ZONA.x0 + ((ZONA.x1 - ZONA.x0) * sel.x) / 100;
    const cy = ZONA.y0 + ((ZONA.y1 - ZONA.y0) * sel.y) / 100;

    // La tinta se abre un poco en el hilo: copias apenas movidas y transparentes.
    const hilo = lienzo();
    const h = hilo.getContext("2d");
    h.globalAlpha = 0.3;
    for (const [ox, oy] of [[-0.8, 0], [0.8, 0], [0, -0.8], [0, 0.8]]) {
      h.drawImage(img, cx - lado / 2 + ox, cy - lado / 2 + oy, lado, lado);
    }
    h.globalAlpha = 1;
    h.drawImage(img, cx - lado / 2, cy - lado / 2, lado, lado);

    const c = lienzo();
    const g = c.getContext("2d");
    g.drawImage(hilo, 0, 0);
    g.globalCompositeOperation = "multiply";
    g.drawImage(capas.cuerpo, 0, 0);           // toma la pelusa y las sombras
    g.globalCompositeOperation = "destination-in";
    g.drawImage(hilo, 0, 0);                   // solo donde está el diseño
    g.drawImage(capas.cuerpo, 0, 0);           // y solo sobre el cuerpo
    return c;
  }

  /** Pinta la calceta completa en un contexto 2D de 600 × 800. */
  function pintar(g, sel) {
    g.clearRect(0, 0, ANCHO, ALTO);
    if (!listo) return;
    g.drawImage(capas.sombra, 0, 0);
    g.drawImage(capaColor("cuerpo", sel.cuerpo), 0, 0);
    const diseno = capaDiseno(sel);
    if (diseno) {
      g.globalAlpha = 0.96;                    // se deja ver un poco el tejido
      g.drawImage(diseno, 0, 0);
      g.globalAlpha = 1;
    }
    g.drawImage(capaColor("detalles", sel.detalles), 0, 0);
  }

  function dibujar() {
    pintar(ctx, leer());
  }

  // ---------------------------------------------------------------- controles
  /** Muestra los porcentajes y desactiva los ajustes cuando no hay diseño. */
  function actualizarControles() {
    const sinDiseno = !disenoElegido();
    ajustes.querySelectorAll("input, button").forEach((el) => { el.disabled = sinDiseno; });
    ajustes.classList.toggle("atenuado", sinDiseno);
    form.querySelectorAll("[data-valor]").forEach((salida) => {
      salida.textContent = `${form.elements[salida.dataset.valor].value} %`;
    });
  }

  // Arrastrar sobre la calceta mueve el diseño (y los controles deslizables).
  let arrastrando = false;
  function mover(e) {
    const caja = canvas.getBoundingClientRect();
    const px = (e.clientX - caja.left) * (ANCHO / caja.width);
    const py = (e.clientY - caja.top) * (ALTO / caja.height);
    const limitar = (v) => Math.min(100, Math.max(0, Math.round(v)));
    form.elements.x.value = limitar(((px - ZONA.x0) / (ZONA.x1 - ZONA.x0)) * 100);
    form.elements.y.value = limitar(((py - ZONA.y0) / (ZONA.y1 - ZONA.y0)) * 100);
    form.dispatchEvent(new Event("input", { bubbles: true }));
  }
  canvas.addEventListener("pointerdown", (e) => {
    if (!disenoElegido()) return;
    arrastrando = true;
    canvas.setPointerCapture(e.pointerId);
    mover(e);
  });
  canvas.addEventListener("pointermove", (e) => { if (arrastrando) mover(e); });
  ["pointerup", "pointercancel"].forEach((t) => canvas.addEventListener(t, () => { arrastrando = false; }));

  document.getElementById("calceta-centrar").addEventListener("click", () => {
    form.elements.x.value = 50;
    form.elements.y.value = 50;
    form.dispatchEvent(new Event("input", { bubbles: true }));
  });

  form.addEventListener("input", () => { actualizarControles(); dibujar(); });

  // ------------------------------------------------------------------- inicio
  canvas.setAttribute("aria-busy", "true");
  const cargadas = Promise.all(
    Object.entries(config.capas).map(([nombre, url]) =>
      cargarImagen(url).then((img) => { capas[nombre] = img; })
    )
  ).then(() => {
    listo = true;
    canvas.removeAttribute("aria-busy");
    dibujar();
  });

  // Imagen pequeña para el carrito y el pedido, igual que en el moño.
  window.Simulador = {
    async vistaPrevia(ancho = 240) {
      try {
        await cargadas;
        const salida = lienzo(ancho, Math.round((ancho * ALTO) / ANCHO));
        const g = salida.getContext("2d");
        g.scale(ancho / ANCHO, ancho / ANCHO);
        pintar(g, leer());
        return salida.toDataURL("image/webp", 0.85);
      } catch (e) {
        return ""; // sin vista previa, el pedido conserva igual las opciones
      }
    },
  };

  actualizarControles();
})();
