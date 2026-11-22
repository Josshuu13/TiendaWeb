"""
Genera la imagen de cada kit navideño juntando las fotos de sus piezas.

Uso:
    python manage.py generar_imagenes_kits

Para cada kit de KITS (en cargar_datos_demo.py) toma las fotos de su suéter,
calcetines y moño (static/img/<categoría>/<slug>.webp), les quita el fondo si lo
tienen, las acomoda sobre un fondo de color suave con una sombra ligera y guarda
el resultado en static/img/kits/<slug>.webp, donde la tienda busca la imagen.

Si cambian las piezas de un kit o la foto de alguna pieza, corran este comando
de nuevo y hagan commit de la imagen.
"""
from pathlib import Path

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFilter

from .cargar_datos_demo import KITS

TAMANO = 800   # la imagen del kit es cuadrada

# Color de fondo de cada kit (tono suave que combina con sus piezas).
FONDOS = {
    "kit-santa": (253, 236, 238),
    "kit-muneco-de-nieve": (236, 242, 248),
    "kit-renos": (234, 238, 248),
    "kit-osito": (236, 246, 238),
}
FONDO_PREDETERMINADO = (248, 242, 234)


def quitar_fondo(imagen):
    """Si la foto tiene fondo liso (sin transparencia), lo vuelve transparente."""
    imagen = imagen.convert("RGBA")
    datos = np.asarray(imagen).astype(int)
    if datos[..., 3].min() < 255:          # ya tiene transparencia: se deja igual
        return imagen.crop(imagen.getbbox())
    fondo = datos[2, 2, :3]                # color de la esquina = color del fondo
    distancia = np.abs(datos[..., :3] - fondo).sum(axis=2)
    alfa = np.clip((distancia - 12) * 12, 0, 255).astype(np.uint8)
    imagen.putalpha(Image.fromarray(alfa).filter(ImageFilter.GaussianBlur(0.6)))
    return imagen.crop(imagen.getbbox())


def ajustar(imagen, ancho, alto):
    """Escala la imagen para que quepa en ancho × alto sin deformarla."""
    escala = min(ancho / imagen.width, alto / imagen.height)
    return imagen.resize((int(imagen.width * escala), int(imagen.height * escala)), Image.LANCZOS)


def pegar_con_sombra(lienzo, imagen, posicion):
    """Pega la imagen con una sombra suave debajo, para que no se vea 'flotando'."""
    sombra = Image.new("RGBA", imagen.size, (0, 0, 0, 0))
    sombra.putalpha(imagen.split()[3].point(lambda v: int(v * 0.22)))
    sombra = sombra.filter(ImageFilter.GaussianBlur(10))
    lienzo.alpha_composite(sombra, (posicion[0] + 6, posicion[1] + 12))
    lienzo.alpha_composite(imagen, posicion)


def armar_kit(fotos, fondo):
    """fotos: [suéter o None, calcetines, moño] ya sin fondo. Devuelve la imagen RGB."""
    sueter, calcetines, mono = fotos
    lienzo = Image.new("RGBA", (TAMANO, TAMANO), fondo + (255,))
    claro = tuple(min(255, c + 8) for c in fondo)
    ImageDraw.Draw(lienzo).ellipse((60, 60, 740, 740), fill=claro + (255,))   # círculo de fondo
    if sueter is not None:
        # Suéter a la izquierda, moño arriba a la derecha y calcetines abajo a la derecha.
        pegar_con_sombra(lienzo, ajustar(sueter, 460, 440), (50, 170))
        pegar_con_sombra(lienzo, ajustar(calcetines, 300, 300), (470, 430))
        pegar_con_sombra(lienzo, ajustar(mono, 300, 440), (500, 50))
    else:
        # Sin suéter: moño a la izquierda y calcetines a la derecha, más grandes.
        pegar_con_sombra(lienzo, ajustar(mono, 340, 520), (70, 140))
        pegar_con_sombra(lienzo, ajustar(calcetines, 380, 380), (400, 230))
    return lienzo.convert("RGB")


class Command(BaseCommand):
    help = "Genera static/img/kits/<slug>.webp juntando las fotos de las piezas de cada kit."

    def add_arguments(self, parser):
        parser.add_argument("--destino", default=None,
                            help="Carpeta donde guardar las imágenes (por defecto static/img/kits).")

    def handle(self, *args, **options):
        imagenes = Path(settings.BASE_DIR) / "static" / "img"
        destino = Path(options["destino"]) if options["destino"] else imagenes / "kits"
        destino.mkdir(parents=True, exist_ok=True)

        for slug, nombre, _precio, sueter, calcetines, mono, _desc in KITS:
            fotos = [
                quitar_fondo(Image.open(imagenes / "sueteres" / f"{sueter}.webp")) if sueter else None,
                quitar_fondo(Image.open(imagenes / "calcetines" / f"{calcetines}.webp")),
                quitar_fondo(Image.open(imagenes / "monos" / f"{mono}.webp")),
            ]
            ruta = destino / f"{slug}.webp"
            armar_kit(fotos, FONDOS.get(slug, FONDO_PREDETERMINADO)).save(ruta, "WEBP", quality=88)
            self.stdout.write(f"  {ruta.name}  ({nombre})")

        self.stdout.write(self.style.SUCCESS(f"Listo: {len(KITS)} imágenes en {destino}"))
