"""
Carga un catálogo de ejemplo para desarrollo y para la demo.

    python manage.py cargar_datos_demo

Se puede ejecutar varias veces: actualiza lo que ya existe en lugar de duplicarlo.
IMPORTANTE: los precios, tiempos y existencias son de ejemplo; reemplácenlos por
los reales desde el panel de administración.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from catalogo.models import Categoria, Color, Decoracion, Parte, Producto, Variante

COLORES = [
    ("Rojo navidad", "#B3122E"),
    ("Verde pino", "#1F5E3A"),
    ("Blanco nieve", "#F4F4F0"),
    ("Dorado", "#C9A227"),
    ("Rosa pastel", "#F4B6C2"),
    ("Azul marino", "#1D2B53"),
    ("Lila", "#B79CD9"),
    ("Amarillo", "#F2C94C"),
    ("Vino", "#6B1E2E"),
    ("Negro", "#1A1A1A"),
]

CATEGORIAS = [
    ("Moños", "monos", "Moños para niña hechos a mano. Diseña el tuyo en el simulador.", 1),
    ("Suéteres navideños", "sueteres", "Suéteres de temporada para toda la familia.", 2),
    ("Calcetines", "calcetines", "Calcetines navideños a juego.", 3),
]

TALLAS_NINA = ["2-4", "6-8", "10-12"]
TALLAS_ADULTO = ["CH", "M", "G"]


class Command(BaseCommand):
    help = "Carga categorías, colores y productos de ejemplo."

    @transaction.atomic
    def handle(self, *args, **options):
        colores = {}
        for i, (nombre, hex_) in enumerate(COLORES):
            colores[nombre], _ = Color.objects.update_or_create(
                nombre=nombre, defaults={"codigo_hex": hex_, "orden": i, "activo": True}
            )

        cats = {}
        for nombre, slug, desc, orden in CATEGORIAS:
            cats[slug], _ = Categoria.objects.update_or_create(
                slug=slug, defaults={"nombre": nombre, "descripcion": desc, "orden": orden}
            )

        # --- Moño personalizable (el que usa el simulador) ---
        clasico, _ = Producto.objects.update_or_create(
            slug="mono-clasico",
            defaults={
                "categoria": cats["monos"],
                "nombre": "Moño clásico personalizable",
                "descripcion": "Elige el color de los lazos y del nudo, agrega una "
                               "decoración y mira cómo queda antes de comprarlo.",
                "precio_base": Decimal("120.00"),
                "dias_elaboracion": 3,
                "personalizable": True,
                "destacado": True,
            },
        )
        todos = list(colores.values())
        for orden, (clave, nombre, inicial) in enumerate(
            [("lazos", "Lazos", "Rojo navidad"), ("nudo", "Nudo", "Blanco nieve")], start=1
        ):
            parte, _ = Parte.objects.update_or_create(
                producto=clasico, clave=clave,
                defaults={"nombre": nombre, "orden": orden, "color_inicial": colores[inicial]},
            )
            parte.colores.set(todos)

        for nombre, clave, precio, dias in [
            ("Perla", "perla", "15.00", 0),
            ("Cascabel", "cascabel", "12.00", 0),
            ("Copo de nieve", "copo", "18.00", 1),
        ]:
            deco, _ = Decoracion.objects.update_or_create(
                clave=clave,
                defaults={"nombre": nombre, "precio_extra": Decimal(precio), "dias_extra": dias},
            )
            deco.productos.add(clasico)

        # --- Moño que se vende tal cual (con existencias) ---
        escolar = self._producto(
            "mono-escolar", cats["monos"], "Moño escolar", "85.00", 0,
            "Moño listo para usar, ideal para el uniforme.", destacado=True,
        )
        for color, stock in [("Rojo navidad", 15), ("Azul marino", 20),
                             ("Blanco nieve", 12), ("Verde pino", 0)]:
            self._variante(escolar, "UNI", colores[color], stock)

        # --- Suéteres ---
        for slug, nombre, precio, color, desc in [
            ("sueter-reno", "Suéter Reno", "450.00", "Rojo navidad",
             "Suéter tejido con reno y copos."),
            ("sueter-copos", "Suéter Copos", "480.00", "Verde pino",
             "Suéter con patrón de copos de nieve."),
        ]:
            p = self._producto(slug, cats["sueteres"], nombre, precio, 0, desc,
                               destacado=slug == "sueter-reno")
            for t in TALLAS_NINA:
                self._variante(p, t, colores[color], 6)
            for t in TALLAS_ADULTO:
                extra = "40.00" if t == "G" else "0"
                self._variante(p, t, colores[color], 4, extra)

        # --- Calcetines ---
        for slug, nombre, precio, desc in [
            ("calcetines-rayas", "Calcetines Rayas navideñas", "95.00",
             "Calcetines a rayas rojo y blanco."),
            ("calcetines-santa", "Calcetines Santa", "110.00",
             "Calcetines con Santa y cascabel."),
        ]:
            p = self._producto(slug, cats["calcetines"], nombre, precio, 0, desc,
                               destacado=slug == "calcetines-santa")
            for t in TALLAS_NINA + ["UNI"]:
                self._variante(p, t, None, 10)

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {Categoria.objects.count()} categorías, {Color.objects.count()} colores, "
            f"{Producto.objects.count()} productos, {Variante.objects.count()} variantes."
        ))

    def _producto(self, slug, categoria, nombre, precio, dias, desc, destacado=False):
        p, _ = Producto.objects.update_or_create(
            slug=slug,
            defaults={
                "categoria": categoria, "nombre": nombre, "descripcion": desc,
                "precio_base": Decimal(precio), "dias_elaboracion": dias,
                "personalizable": False, "destacado": destacado,
            },
        )
        return p

    def _variante(self, producto, talla, color, existencias, extra="0"):
        sufijo = color.nombre.split()[0][:3].upper() if color else "STD"
        sku = f"{producto.slug.upper()[:12]}-{talla}-{sufijo}"
        Variante.objects.update_or_create(
            producto=producto, talla=talla, color=color,
            defaults={"sku": sku, "existencias": existencias, "precio_extra": Decimal(extra)},
        )
