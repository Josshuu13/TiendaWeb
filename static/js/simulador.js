/*
 * simulador.js — Simulador visual del moño con fotografías reales.
 *
 * Cómo funciona:
 *   - El moño está separado en capas PNG en escala de grises (patas, base de abajo,
 *     base de arriba, decorado, tiras y nudo). Todas miden lo mismo y encajan.
 *   - Para pintar una capa se usa la fusión "multiply": lo claro de la foto queda
 *     del color elegido y las sombras quedan del mismo color, pero más oscuro.
 *     Así se conservan la textura del listón, los pliegues y el volumen.
 *   - Las capas se dibujan en orden (de atrás hacia adelante) sobre el <canvas>.
 *   - Si el cliente elige un listón estampado para el decorado, la foto del
 *     listón se "estampa" sobre esa capa siguiendo un mapa (decorado-uv.png) que
 *     indica en qué punto del ancho del listón cae cada píxel, y se le aplican
 *     las sombras de la foto original.
 *
 * Recibe la selección desde cotizador.js con el evento "seleccion-cambiada":
 *   { colores: { patas: "#B3122E", ... }, estampado: "tejido-rojo" | null }
 * No sabe nada de precios: eso lo calcula el servidor.
 */
(function () {
  const canvas = document.getElementById("simulador");
  const datosConfig = document.getElementById("config-simulador");
  if (!canvas || !datosConfig) return; // esta página no tiene simulador

  const config = JSON.parse(datosConfig.textContent);
  const ctx = canvas.getContext("2d");
  const avisoCargando = document.getElementById("simulador-cargando");

  // ------------------------------------------------------------------ estado
  const capas = [];            // [{clave, img}] en orden de dibujo
  let mapaUV = null;           // ImageData del mapa del decorado (canal rojo = posición u)
  const tiras = {};            // estampado -> ImageData de la tira del listón
  const cacheColor = new Map(); // "clave|#hex" -> canvas ya pintado
  const cacheEstampado = new Map(); // "clave|estampado" -> canvas ya estampado
  let seleccion = null;        // última selección recibida
  let listo = false;           // true cuando cargaron todas las capas

  // Escuchar la selección desde el principio (puede llegar antes de que carguen las fotos).
  document.addEventListener("seleccion-cambiada", (e) => {
    seleccion = e.detail;
    if (listo) dibujar();
  });

  // ------------------------------------------------------------ utilidades
  /** Carga una imagen y devuelve una promesa que se resuelve cuando termina. */
  function cargarImagen(url) {
    return new Promise((resolver, rechazar) => {
      const img = new Image();
      img.onload = () => resolver(img);
      img.onerror = () => rechazar(new Error("No se pudo cargar " + url));
      img.src = url;
    });
  }

  /** Crea un canvas auxiliar (no visible) del mismo tamaño que el simulador. */
  function lienzo() {
    const c = document.createElement("canvas");
    c.width = canvas.width;
    c.height = canvas.height;
    return c;
  }

  /** Lee los píxeles de una imagen como ImageData. */
  function pixeles(img, ancho = img.naturalWidth, alto = img.naturalHeight) {
    const c = document.createElement("canvas");
    c.width = ancho;
    c.height = alto;
    const g = c.getContext("2d");
    g.drawImage(img, 0, 0, ancho, alto);
    return g.getImageData(0, 0, ancho, alto);
  }

  // ------------------------------------------------------------ pintar capas
  /** Capa teñida de un color liso (fusión multiply), con caché. */
  function capaColor(capa, hex) {
    const llave = capa.clave + "|" + hex;
    if (cacheColor.has(llave)) return cacheColor.get(llave);

    const c = lienzo();
    const g = c.getContext("2d");
    g.drawImage(capa.img, 0, 0);                  // 1) foto gris de la capa
    g.globalCompositeOperation = "multiply";
    g.fillStyle = hex;
    g.fillRect(0, 0, c.width, c.height);          // 2) multiplica por el color
    g.globalCompositeOperation = "destination-in";
    g.drawImage(capa.img, 0, 0);                  // 3) recorta a la forma de la capa
    cacheColor.set(llave, c);
    return c;
  }

  /** Mide el ancho de una cola del decorado (en píxeles), para escalar el estampado. */
  function anchoCola(datos) {
    const { width, height, data } = datos;
    const anchos = [];
    for (let y = Math.round(height * 0.40); y < height * 0.50; y += 4) {
      let x = 0;
      while (x < width && data[(y * width + x) * 4 + 3] < 128) x++;   // inicio de la cola
      const inicio = x;
      while (x < width && data[(y * width + x) * 4 + 3] >= 128) x++;  // fin de la cola
      if (x - inicio > 40) anchos.push(x - inicio);
    }
    anchos.sort((a, b) => a - b);
    return anchos.length ? anchos[Math.floor(anchos.length / 2)] : width / 4;
  }

  /** Capa con un listón estampado aplicado, con caché. */
  function capaEstampada(capa, claveEstampado) {
    const llave = capa.clave + "|" + claveEstampado;
    if (cacheEstampado.has(llave)) return cacheEstampado.get(llave);

    const tira = tiras[claveEstampado];
    const base = pixeles(capa.img, canvas.width, canvas.height); // gris + transparencia
    const { width: W, height: H } = base;
    const gris = base.data;
    const uv = mapaUV.data;

    // Brillo de referencia: el 88 % más claro de la capa, para calcular las sombras.
    const histograma = new Uint32Array(256);
    let total = 0;
    for (let i = 0; i < gris.length; i += 4) {
      if (gris[i + 3] > 128) { histograma[gris[i]]++; total++; }
    }
    let acumulado = 0, referencia = 255;
    for (let v = 0; v < 256; v++) {
      acumulado += histograma[v];
      if (acumulado >= total * 0.88) { referencia = Math.max(v, 1); break; }
    }

    const tw = tira.width, th = tira.height, td = tira.data;
    const escala = tw / anchoCola(base); // px de la tira por px del moño
    const salida = new ImageData(W, H);
    const out = salida.data;

    for (let y = 0; y < H; y++) {
      // Posición vertical en la tira; se refleja (espejo) para que no se note la unión.
      let v = Math.floor(y * escala) % (2 * th);
      if (v >= th) v = 2 * th - 1 - v;
      for (let x = 0; x < W; x++) {
        const i = (y * W + x) * 4;
        const a = gris[i + 3];
        if (a === 0) continue;                          // fuera del decorado
        const u = Math.min(tw - 1, Math.round((uv[i] / 255) * (tw - 1))); // posición en el ancho
        const sombra = Math.min(gris[i] / referencia, 1.12);              // sombra de la foto
        const j = (v * tw + u) * 4;
        out[i] = Math.min(255, td[j] * sombra);
        out[i + 1] = Math.min(255, td[j + 1] * sombra);
        out[i + 2] = Math.min(255, td[j + 2] * sombra);
        out[i + 3] = a;
      }
    }
    const c = lienzo();
    c.getContext("2d").putImageData(salida, 0, 0);
    cacheEstampado.set(llave, c);
    return c;
  }

  /** Carga (una sola vez) la foto de un estampado. */
  async function prepararEstampado(clave) {
    if (tiras[clave]) return true;
    const url = config.estampados[clave];
    if (!url) return false;
    try {
      tiras[clave] = pixeles(await cargarImagen(url));
      if (!mapaUV) mapaUV = pixeles(await cargarImagen(config.mapa_estampado), canvas.width, canvas.height);
      return true;
    } catch (e) {
      console.error(e);
      return false;
    }
  }

  // ------------------------------------------------------------ resaltar parte
  /*
   * Cuando el cliente cambia de paso (personalizador.js manda "parte-activa"),
   * la parte elegida se queda con su color y las demás se aclaran un momento,
   * para que se entienda qué pieza del moño se está cambiando.
   */
  const etiqueta = document.getElementById("simulador-etiqueta");
  const DURACION_RESALTADO = 1300; // milisegundos
  let resaltada = null;            // clave de la parte resaltada (o null)
  let temporizadorResaltado = null;

  document.addEventListener("parte-activa", (e) => {
    resaltada = e.detail.clave;
    if (etiqueta) {
      etiqueta.textContent = e.detail.nombre;
      etiqueta.classList.add("visible");
    }
    if (listo) dibujar();
    clearTimeout(temporizadorResaltado);
    temporizadorResaltado = setTimeout(() => {
      resaltada = null;
      if (etiqueta) etiqueta.classList.remove("visible");
      if (listo) dibujar();
    }, DURACION_RESALTADO);
  });

  // ------------------------------------------------------------ dibujar
  /** Dibuja el moño completo con la selección actual. */
  async function dibujar() {
    if (!seleccion) return;
    const { colores, estampado } = seleccion;
    const usarEstampado = estampado && (await prepararEstampado(estampado));

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const capa of capas) {
      // Si hay una parte resaltada, las demás se dibujan casi transparentes.
      ctx.globalAlpha = resaltada && resaltada !== capa.clave ? 0.18 : 1;
      if (usarEstampado && config.estampables.includes(capa.clave)) {
        ctx.drawImage(capaEstampada(capa, estampado), 0, 0);
      } else {
        ctx.drawImage(capaColor(capa, colores[capa.clave] || "#FFFFFF"), 0, 0);
      }
    }
    ctx.globalAlpha = 1;
  }

  /**
   * Imagen pequeña del moño, sin resaltados ni zoom, para mostrarla en el carrito y en
   * el pedido. Se pinta en un canvas aparte para no tocar lo que ve el cliente.
   */
  async function vistaPrevia(ancho = 300) {
    if (!listo || !seleccion) return "";
    const { colores, estampado } = seleccion;
    const usarEstampado = estampado && (await prepararEstampado(estampado));
    const salida = document.createElement("canvas");
    salida.width = ancho;
    salida.height = Math.round(canvas.height * (ancho / canvas.width));
    const g = salida.getContext("2d");
    for (const capa of capas) {
      const imagen = usarEstampado && config.estampables.includes(capa.clave)
        ? capaEstampada(capa, estampado)
        : capaColor(capa, colores[capa.clave] || "#FFFFFF");
      g.drawImage(imagen, 0, 0, salida.width, salida.height);
    }
    return salida.toDataURL("image/webp", 0.8);
  }
  window.Simulador = { vistaPrevia };

  // ------------------------------------------------------------ zoom y arrastre
  /*
   * El zoom NO vuelve a dibujar el moño: solo agranda el canvas con CSS
   * (transform: scale) dentro del visor, que recorta lo que sobra.
   * Con zoom mayor a 100 % se puede arrastrar el moño para ver otras zonas.
   */
  const visor = document.getElementById("simulador-visor");
  const etiquetaZoom = document.getElementById("zoom-valor");
  const ZOOM_MIN = 1, ZOOM_MAX = 4;
  let zoom = 1, despX = 0, despY = 0; // nivel de zoom y desplazamiento en píxeles

  /** Evita que el moño se arrastre fuera del visor. */
  function limitarDesplazamiento() {
    const maxX = Math.max(0, (canvas.offsetWidth * zoom - visor.clientWidth) / 2);
    const maxY = Math.max(0, (canvas.offsetHeight * zoom - visor.clientHeight) / 2);
    despX = Math.min(maxX, Math.max(-maxX, despX));
    despY = Math.min(maxY, Math.max(-maxY, despY));
  }

  /** Aplica el zoom y el desplazamiento actuales al canvas. */
  function aplicarZoom() {
    limitarDesplazamiento();
    canvas.style.transform = `translate(${despX}px, ${despY}px) scale(${zoom})`;
    if (etiquetaZoom) etiquetaZoom.textContent = Math.round(zoom * 100) + " %";
  }

  /** Cambia el zoom a un nivel nuevo (entre 100 % y 400 %). */
  function ponerZoom(nuevo) {
    zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, nuevo));
    if (zoom === 1) { despX = 0; despY = 0; } // al 100 % el moño vuelve al centro
    aplicarZoom();
  }

  if (visor) {
    // Botones − / + / Ver completo
    document.querySelectorAll("[data-zoom]").forEach((boton) => {
      boton.addEventListener("click", () => {
        const accion = boton.dataset.zoom;
        if (accion === "+") ponerZoom(zoom * 1.5);
        else if (accion === "-") ponerZoom(zoom / 1.5);
        else ponerZoom(1);
      });
    });

    // Rueda del mouse sobre el moño: acercar o alejar (sin mover la página)
    visor.addEventListener("wheel", (e) => {
      e.preventDefault();
      ponerZoom(zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15));
    }, { passive: false });

    // Doble clic: alterna entre ver completo y acercar al 200 %
    visor.addEventListener("dblclick", () => ponerZoom(zoom > 1 ? 1 : 2));

    // Arrastrar con mouse o dedo para mover el moño cuando hay zoom
    let inicio = null;
    visor.addEventListener("pointerdown", (e) => {
      if (zoom === 1) return;
      inicio = { x: e.clientX - despX, y: e.clientY - despY };
      visor.setPointerCapture(e.pointerId);
      visor.classList.add("arrastrando");
    });
    visor.addEventListener("pointermove", (e) => {
      if (!inicio) return;
      despX = e.clientX - inicio.x;
      despY = e.clientY - inicio.y;
      aplicarZoom();
    });
    const soltar = () => { inicio = null; visor.classList.remove("arrastrando"); };
    visor.addEventListener("pointerup", soltar);
    visor.addEventListener("pointercancel", soltar);

    // Si cambia el tamaño de la ventana, se reacomodan los límites
    window.addEventListener("resize", aplicarZoom);
  }

  // ------------------------------------------------------------ inicio
  (async function iniciar() {
    try {
      const imgs = await Promise.all(config.capas.map((c) => cargarImagen(c.url)));
      canvas.width = imgs[0].naturalWidth;   // tamaño real de las fotos
      canvas.height = imgs[0].naturalHeight;
      config.capas.forEach((c, i) => capas.push({ clave: c.clave, img: imgs[i] }));
      listo = true;
      if (avisoCargando) avisoCargando.remove();
      dibujar();
    } catch (e) {
      console.error(e);
      if (avisoCargando) avisoCargando.textContent = "No se pudo cargar el simulador.";
    }
  })();
})();
