"""
Genera las imágenes de los moños "listos para usar" a partir de las capas del simulador.

Uso:
    python manage.py generar_imagenes_monos

Hace lo mismo que el simulador en el navegador, pero en Python (con Pillow):
toma la foto gris de cada parte del moño, la pinta con la fusión "multiply"
(lo claro toma el color y las sombras se conservan) y pone las capas una encima
de otra. El resultado se guarda en static/img/monos/<slug>.webp, que es donde
la tienda busca la imagen de cada producto.

Cuando agreguen un diseño nuevo a DISENOS_LISTOS (en cargar_datos_demo.py),
corran este comando para crear su imagen y luego hagan commit de la imagen.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageChops

from .cargar_datos_demo import COLORES, DISENOS_LISTOS, PARTES_MONO

# Tamaño máximo de la imagen final (el mismo orden de tamaño que las demás fotos).
TAMANO_MAXIMO = (600, 900)


def _a_rgb(codigo_hex):
    """'#1C2541' -> (28, 37, 65)"""
    codigo_hex = codigo_hex.lstrip("#")
    return tuple(int(codigo_hex[i:i + 2], 16) for i in (0, 2, 4))


def pintar_mono(carpeta_capas, colores_por_parte, hex_por_nombre):
    """Devuelve una imagen RGBA del moño con cada parte pintada de su color."""
    lienzo = None
    for clave, *_ in PARTES_MONO:           # PARTES_MONO ya está en orden de dibujo
        capa = Image.open(carpeta_capas / f"{clave}.png").convert("LA")
        gris, alfa = capa.split()
        foto = Image.merge("RGB", (gris, gris, gris))
        color = Image.new("RGB", foto.size, _a_rgb(hex_por_nombre[colores_por_parte[clave]]))
        pintada = ImageChops.multiply(foto, color)   # fusión "multiply"
        pintada.putalpha(alfa)                        # recorta a la forma de la parte
        if lienzo is None:
            lienzo = Image.new("RGBA", foto.size, (0, 0, 0, 0))
        lienzo = Image.alpha_composite(lienzo, pintada)
    lienzo = lienzo.crop(lienzo.getbbox())            # quita el espacio vacío alrededor
    lienzo.thumbnail(TAMANO_MAXIMO)
    return lienzo


class Command(BaseCommand):
    help = "Genera static/img/monos/<slug>.webp para cada diseño listo para usar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--destino", default=None,
            help="Carpeta donde guardar las imágenes (por defecto static/img/monos).",
        )

    def handle(self, *args, **options):
        estaticos = Path(settings.BASE_DIR) / "static"
        carpeta_capas = estaticos / "simulador" / "mono-clasico"
        destino = Path(options["destino"]) if options["destino"] else estaticos / "img" / "monos"
        destino.mkdir(parents=True, exist_ok=True)
        hex_por_nombre = {nombre: codigo for nombre, codigo, _ in COLORES}

        for slug, nombre, por_parte in DISENOS_LISTOS:
            imagen = pintar_mono(carpeta_capas, por_parte, hex_por_nombre)
            ruta = destino / f"{slug}.webp"
            imagen.save(ruta, "WEBP", quality=88)
            self.stdout.write(f"  {ruta.name}  ({nombre})")

        self.stdout.write(self.style.SUCCESS(f"Listo: {len(DISENOS_LISTOS)} imágenes en {destino}"))
