"""
Genera las imágenes de los moños "listos para usar" a partir de las capas del simulador.

Uso:
    python manage.py generar_imagenes_monos

Hace lo mismo que el simulador en el navegador, pero en Python (con Pillow y NumPy):
toma la foto gris de cada parte del moño, la pinta con la fusión "multiply"
(lo claro toma el color y las sombras se conservan) y pone las capas una encima
de otra. Si el diseño lleva un listón estampado, el decorado se cubre con la foto
del listón usando el mapa decorado-uv.png, igual que simulador.js.

El resultado se guarda en static/img/monos/<slug>.webp, que es donde la tienda
busca la imagen de cada producto.

Cuando agreguen un diseño nuevo (DISENOS_LISTOS, DISENOS_NAVIDENOS o
DISENOS_CON_DECORADO en cargar_datos_demo.py), corran este comando para crear su
imagen y luego hagan commit de la imagen.
"""
from pathlib import Path

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageChops

from .cargar_datos_demo import COLORES, PARTES_MONO, TODOS_LOS_DISENOS

# Tamaño máximo de la imagen final (el mismo orden de tamaño que las demás fotos).
TAMANO_MAXIMO = (600, 900)


def _a_rgb(codigo_hex):
    """'#1C2541' -> (28, 37, 65)"""
    codigo_hex = codigo_hex.lstrip("#")
    return tuple(int(codigo_hex[i:i + 2], 16) for i in (0, 2, 4))


def _ancho_cola(alfa):
    """Ancho típico (en píxeles) de una cola del decorado, para escalar el estampado.
    Mismo cálculo que anchoCola() en simulador.js."""
    alto = alfa.shape[0]
    anchos = []
    for y in range(round(alto * 0.40), int(alto * 0.50), 4):
        fila = alfa[y] >= 128
        x = int(np.argmax(fila)) if fila.any() else len(fila)   # inicio de la cola
        fin = x
        while fin < len(fila) and fila[fin]:
            fin += 1
        if fin - x > 40:
            anchos.append(fin - x)
    return sorted(anchos)[len(anchos) // 2] if anchos else alfa.shape[1] / 4


def estampar(capa_gris, capa_alfa, mapa_uv, tira):
    """Cubre una capa (gris + transparencia) con la foto de un listón estampado.
    Mismo cálculo que capaEstampada() en simulador.js."""
    gris = np.asarray(capa_gris, np.float32)
    alfa = np.asarray(capa_alfa)
    uv = np.asarray(mapa_uv, np.float32)
    t = np.asarray(tira.convert("RGB"), np.float32)
    th, tw = t.shape[:2]

    # Brillo de referencia: el 88 % más claro de la capa, para calcular las sombras.
    referencia = max(np.percentile(gris[alfa > 128], 88), 1)
    escala = tw / _ancho_cola(alfa)                     # px de la tira por px del moño

    alto, ancho = gris.shape
    v = (np.arange(alto) * escala).astype(int) % (2 * th)
    v = np.where(v >= th, 2 * th - 1 - v, v)           # espejo para que no se note la unión
    u = np.clip(np.round(uv / 255 * (tw - 1)).astype(int), 0, tw - 1)
    sombra = np.minimum(gris / referencia, 1.12)[..., None]
    rgb = np.clip(t[v[:, None], u] * sombra, 0, 255).astype(np.uint8)
    imagen = Image.fromarray(rgb)
    imagen.putalpha(capa_alfa)
    return imagen


def pintar_mono(carpeta_capas, colores_por_parte, hex_por_nombre, tira=None):
    """Devuelve una imagen RGBA del moño con cada parte pintada de su color.
    Si se da `tira` (foto de un listón estampado), el decorado se estampa con ella."""
    lienzo = None
    for clave, *_ in PARTES_MONO:           # PARTES_MONO ya está en orden de dibujo
        capa = Image.open(carpeta_capas / f"{clave}.png").convert("LA")
        gris, alfa = capa.split()
        if tira is not None and clave == "decorado":
            pintada = estampar(gris, alfa, Image.open(carpeta_capas / "decorado-uv.png").convert("L"), tira)
        else:
            foto = Image.merge("RGB", (gris, gris, gris))
            color = Image.new("RGB", foto.size, _a_rgb(hex_por_nombre[colores_por_parte[clave]]))
            pintada = ImageChops.multiply(foto, color)   # fusión "multiply"
            pintada.putalpha(alfa)                        # recorta a la forma de la parte
        if lienzo is None:
            lienzo = Image.new("RGBA", capa.size, (0, 0, 0, 0))
        lienzo = Image.alpha_composite(lienzo, pintada)
    lienzo = lienzo.crop(lienzo.getbbox())            # quita el espacio vacío alrededor
    lienzo.thumbnail(TAMANO_MAXIMO)
    return lienzo


class Command(BaseCommand):
    help = "Genera static/img/monos/<slug>.webp para cada moño listo para usar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--destino", default=None,
            help="Carpeta donde guardar las imágenes (por defecto static/img/monos).",
        )

    def handle(self, *args, **options):
        estaticos = Path(settings.BASE_DIR) / "static"
        carpeta_capas = estaticos / "simulador" / "mono-clasico"
        carpeta_estampados = estaticos / "simulador" / "estampados"
        destino = Path(options["destino"]) if options["destino"] else estaticos / "img" / "monos"
        destino.mkdir(parents=True, exist_ok=True)
        hex_por_nombre = {nombre: codigo for nombre, codigo, _ in COLORES}

        for slug, nombre, por_parte, estampado, _coleccion in TODOS_LOS_DISENOS:
            tira = Image.open(carpeta_estampados / f"{estampado}.jpg") if estampado else None
            imagen = pintar_mono(carpeta_capas, por_parte, hex_por_nombre, tira)
            ruta = destino / f"{slug}.webp"
            imagen.save(ruta, "WEBP", quality=88)
            self.stdout.write(f"  {ruta.name}  ({nombre})")

        self.stdout.write(self.style.SUCCESS(f"Listo: {len(TODOS_LOS_DISENOS)} imágenes en {destino}"))
