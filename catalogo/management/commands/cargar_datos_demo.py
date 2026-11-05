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

from catalogo.models import (
    Categoria, Color, Combinacion, CombinacionParte, Estampado, Parte, Producto, Variante,
)

# ---------------------------------------------------------------------------
# Paleta de listón grosgrain: los colores más buscados para moños escolares
# (colores de uniforme) y para temporada navideña, más algunos básicos.
# (nombre, código hexadecimal, grupo)
# ---------------------------------------------------------------------------
COLORES = [
    # Escolares (colores comunes de uniforme en México)
    ("Blanco", "#F7F7F4", Color.ESCOLAR),
    ("Azul marino", "#1C2541", Color.ESCOLAR),
    ("Azul rey", "#1F4FB4", Color.ESCOLAR),
    ("Celeste", "#8EC1E6", Color.ESCOLAR),
    ("Guinda", "#6E1428", Color.ESCOLAR),
    ("Verde botella", "#0F4D32", Color.ESCOLAR),
    ("Gris Oxford", "#4A4E54", Color.ESCOLAR),
    ("Café", "#4E2E1E", Color.ESCOLAR),
    ("Amarillo oro", "#E8B517", Color.ESCOLAR),
    ("Negro", "#161616", Color.ESCOLAR),
    # Navideños
    ("Rojo navidad", "#B3122E", Color.NAVIDENO),
    ("Verde pino", "#1F5E3A", Color.NAVIDENO),
    ("Verde navidad", "#2E8B3E", Color.NAVIDENO),
    ("Vino", "#6B1E2E", Color.NAVIDENO),
    ("Dorado", "#C9A227", Color.NAVIDENO),
    ("Plateado", "#B9BCC2", Color.NAVIDENO),
    ("Crema", "#EFE6D2", Color.NAVIDENO),
    # Básicos y pastel
    ("Rosa pastel", "#F4B6C2", Color.BASICO),
    ("Rosa mexicano", "#E4007C", Color.BASICO),
    ("Lila", "#B79CD9", Color.BASICO),
    ("Turquesa", "#2BB3B1", Color.BASICO),
]

CATEGORIAS = [
    ("Moños", "monos", "Moños para niña hechos a mano. Diseña el tuyo en el simulador.", 1),
    ("Suéteres navideños", "sueteres", "Suéteres de temporada para toda la familia.", 2),
    ("Calcetines", "calcetines", "Calcetines navideños a juego.", 3),
]

# Partes del moño personalizable, en orden de dibujo (de atrás hacia adelante).
# (clave, nombre visible, color inicial, ¿admite estampado?, paso en que el cliente la elige)
PARTES_MONO = [
    ("patas", "Patas", "Rojo navidad", False, 1),
    ("baseabajo", "Base inferior", "Blanco", False, 3),
    ("basearriba", "Base superior", "Rojo navidad", False, 2),
    ("decorado", "Decorado", "Verde pino", True, 4),
    ("tiras", "Tiras", "Blanco", False, 5),
    ("nudo", "Nudo", "Rojo navidad", False, 6),
]

# Combinaciones de ejemplo para "Lo más vendido".
# (nombre, {parte: color}, estampado o None). Cámbienlas por las reales en el admin.
COMBINACIONES = [
    ("Navidad clásica", {"patas": "Rojo navidad", "basearriba": "Rojo navidad", "baseabajo": "Blanco",
                         "decorado": "Verde pino", "tiras": "Blanco", "nudo": "Rojo navidad"}, None),
    ("Vino y dorado", {"patas": "Vino", "basearriba": "Dorado", "baseabajo": "Vino",
                       "decorado": "Vino", "tiras": "Dorado", "nudo": "Dorado"}, None),
    ("Pino y nieve", {"patas": "Verde pino", "basearriba": "Blanco", "baseabajo": "Verde pino",
                      "decorado": "Rojo navidad", "tiras": "Blanco", "nudo": "Verde pino"}, None),
    ("Escolar marino", {"patas": "Azul marino", "basearriba": "Blanco", "baseabajo": "Azul marino",
                        "decorado": "Azul marino", "tiras": "Blanco", "nudo": "Azul marino"}, None),
]

# Listones estampados de ejemplo (sus imágenes están en static/simulador/estampados/).
ESTAMPADOS = [
    ("Tejido rojo", "tejido-rojo", "25.00"),
    ("Rombos verde", "rombos-verde", "25.00"),
]

TALLAS_NINA = ["2-4", "6-8", "10-12"]
TALLAS_ADULTO = ["CH", "M", "G"]


class Command(BaseCommand):
    help = "Carga categorías, colores, el moño del simulador y productos de ejemplo."

    @transaction.atomic  # si algo falla a la mitad, no se guarda nada
    def handle(self, *args, **options):
        # --- Colores: se crean/actualizan y se desactivan los que ya no están ---
        colores = {}
        for i, (nombre, hex_, grupo) in enumerate(COLORES):
            colores[nombre], _ = Color.objects.update_or_create(
                nombre=nombre,
                defaults={"codigo_hex": hex_, "grupo": grupo, "orden": i, "activo": True},
            )
        Color.objects.exclude(nombre__in=colores).update(activo=False)

        # --- Categorías ---
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
                "descripcion": "Elige el color de cada parte del moño o un listón "
                               "estampado para el decorado, y mira cómo queda antes "
                               "de comprarlo.",
                "precio_base": Decimal("120.00"),
                "dias_elaboracion": 3,
                "personalizable": True,
                "destacado": True,
            },
        )
        # Se borran partes viejas (por ejemplo "lazos" de la versión anterior).
        claves = [p[0] for p in PARTES_MONO]
        clasico.partes.exclude(clave__in=claves).delete()
        todos = list(colores.values())
        partes = {}
        for orden, (clave, nombre, inicial, estampable, paso) in enumerate(PARTES_MONO, start=1):
            parte, _ = Parte.objects.update_or_create(
                producto=clasico, clave=clave,
                defaults={
                    "nombre": nombre,
                    "orden": orden,          # orden de dibujo
                    "paso": paso,            # orden en que el cliente la elige
                    "color_inicial": colores[inicial],
                    "admite_estampado": estampable,
                },
            )
            parte.colores.set(todos)  # todas las partes aceptan toda la paleta
            partes[clave] = parte

        for i, (nombre, clave, precio) in enumerate(ESTAMPADOS):
            est, _ = Estampado.objects.update_or_create(
                clave=clave,
                defaults={"nombre": nombre, "precio_extra": Decimal(precio), "orden": i},
            )
            est.productos.add(clasico)

        # --- Combinaciones de "Lo más vendido" ---
        for i, (nombre, por_parte, clave_est) in enumerate(COMBINACIONES):
            combo, _ = Combinacion.objects.update_or_create(
                producto=clasico, nombre=nombre,
                defaults={
                    "orden": i, "activa": True,
                    "estampado": Estampado.objects.filter(clave=clave_est).first() if clave_est else None,
                },
            )
            for clave, color in por_parte.items():
                CombinacionParte.objects.update_or_create(
                    combinacion=combo, parte=partes[clave], defaults={"color": colores[color]}
                )

        # --- Moño escolar que se vende tal cual (con existencias) ---
        escolar = self._producto(
            "mono-escolar", cats["monos"], "Moño escolar", "85.00", 0,
            "Moño listo para usar, en los colores de uniforme más comunes.", destacado=True,
        )
        stock_escolar = {"Azul marino": 20, "Guinda": 15, "Blanco": 12, "Verde botella": 0}
        # Quitar variantes de colores anteriores para no chocar con los SKU nuevos.
        escolar.variantes.exclude(color__nombre__in=stock_escolar).delete()
        for color, stock in stock_escolar.items():
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
                extra = "40.00" if t == "G" else "0"  # la talla G cuesta $40 más
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
            f"Listo: {Categoria.objects.count()} categorías, "
            f"{Color.objects.filter(activo=True).count()} colores activos, "
            f"{Producto.objects.count()} productos, {Variante.objects.count()} variantes, "
            f"{clasico.partes.count()} partes del moño, {Estampado.objects.count()} estampados, "
            f"{clasico.combinaciones.count()} combinaciones."
        ))

    # ----------------------------------------------------------------- auxiliares
    def _producto(self, slug, categoria, nombre, precio, dias, desc, destacado=False):
        """Crea o actualiza un producto de catálogo (no personalizable)."""
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
        """Crea o actualiza una variante. El SKU se arma con producto, talla y color."""
        sufijo = "".join(w[:3] for w in color.nombre.split()).upper() if color else "STD"
        sku = f"{producto.slug.upper()[:12]}-{talla}-{sufijo}"
        Variante.objects.update_or_create(
            producto=producto, talla=talla, color=color,
            defaults={"sku": sku, "existencias": existencias, "precio_extra": Decimal(extra)},
        )
