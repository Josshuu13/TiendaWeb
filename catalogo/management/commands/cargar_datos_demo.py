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
    Categoria, Color, Combinacion, CombinacionParte, Estampado, Parte, Producto, Temporada, Variante,
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
    # Agregados el 08/11/2026. Revisen que cada tono corresponda a un listón que
    # realmente tengan o puedan comprar, y ajusten el código si su listón es distinto.
    ("Jade", "#00A86B", Color.BASICO),
    ("Naranja", "#F2711C", Color.BASICO),
    ("Palo de rosa", "#D8A7A0", Color.BASICO),
    ("Café arena", "#C2A27C", Color.BASICO),
    ("Azul turquesa", "#30B5C8", Color.BASICO),
]

CATEGORIAS = [
    ("Moños", "monos", "Diseña el tuyo en el simulador o elige uno listo para el uniforme.", 1),
    ("Suéteres navideños", "sueteres", "Tallas para niña y adulto. Cambio de talla sin costo.", 2),
    ("Calcetines", "calcetines", "Diseños navideños que combinan con todo.", 3),
    ("Kits navideños", "kits", "Moño, suéter y calcetines a juego. Más fácil de regalar y con descuento.", 4),
]

# Kits navideños de ejemplo: (slug, nombre, precio, precio sin descuento, color, descripción)
KITS = [
    ("kit-reno-rojo", "Kit Reno rojo", "580.00", "680.00", "Rojo navidad",
     "Moño navideño + Suéter Santa + Calcetines Santa, en rojo a juego."),
    ("kit-pino", "Kit Pino", "590.00", "695.00", "Verde pino",
     "Moño verde pino + Suéter Osito + Calcetines Rayas."),
    ("kit-vino-dorado", "Kit Vino y dorado", "585.00", "685.00", "Vino",
     "Moño vino y dorado + suéter + calcetines, ideal para posadas."),
    ("kit-escolar", "Kit Escolar", "170.00", "195.00", "Azul marino",
     "Moño escolar + calcetines (sin suéter), en colores de uniforme."),
]

# Suéteres: (slug, nombre, precio, color, descripción). Cada diseño es un producto con su
# imagen en static/img/sueteres/<slug>.webp. Para agregar uno nuevo basta con un renglón
# aquí y su imagen.
SUETERES = [
    ("sueter-renos-azul", "Suéter Renos azul marino", "450.00", "Azul marino",
     "Dos renos tejidos entre copos de nieve y una franja de pinos. Abrigador y perfecto para posadas."),
    ("sueter-santa", "Suéter Santa", "480.00", "Rojo navidad",
     "Santa Claus al frente con pinos y renos en la parte baja. El clásico de las fotos familiares."),
    ("sueter-muneco-nieve", "Suéter Muñeco de nieve", "450.00", "Gris Oxford",
     "Muñeco de nieve con bufanda roja sobre tejido gris. Combina con moños de cualquier color."),
    ("sueter-osito", "Suéter Osito", "470.00", "Verde pino",
     "Osito con gorro de Santa, copos y corazones. Tierno y fácil de combinar con rojo o dorado."),
    ("sueter-merry-christmas", "Suéter Merry Christmas", "480.00", "Negro",
     "Reno sonriente con letras Merry Christmas sobre tejido negro."),
]
# Guía de tallas de los suéteres; cada categoría puede tener la suya.
GUIA_TALLAS_SUETERES = """2-4: niña de 2 a 4 años
6-8: niña de 6 a 8 años
10-12: niña de 10 a 12 años
CH / M / G: adulto, pecho de 88-94 / 96-102 / 104-110 cm"""

# Suéteres de la primera versión: dejan de mostrarse en la tienda.
SUETERES_RETIRADOS = ["sueter-reno", "sueter-copos"]

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

# ---------------------------------------------------------------------------
# Diseños listos para usar: moños de uniforme que se venden tal cual, sin pasar
# por el simulador (por eso cuestan menos). Cada diseño es un producto.
#
# Para cada parte se indica su color. Para los de 2 colores se usa la función
# dos_colores(), que siempre reparte igual:
#   primer color  -> base superior, patas, tiras y nudo
#   segundo color -> base inferior y decorado (el lazo grande del frente)
# Así, el orden del nombre decide qué color se ve al frente.
#
# Las imágenes (static/img/monos/<slug>.webp) se generan con las capas del
# simulador:  python manage.py generar_imagenes_monos
# ---------------------------------------------------------------------------
PRECIO_DISENO_LISTO = "85.00"   # precio provisional; cámbienlo aquí o en el admin


def un_color(color, tiras="Blanco"):
    """Moño de un solo color con tiras blancas (los "clásicos")."""
    return {"patas": color, "baseabajo": color, "basearriba": color,
            "decorado": color, "tiras": tiras, "nudo": color}


def dos_colores(primero, segundo):
    """Moño de 2 colores con la estructura acordada (ver arriba)."""
    return {"basearriba": primero, "patas": primero, "tiras": primero, "nudo": primero,
            "baseabajo": segundo, "decorado": segundo}


# (slug, nombre, {parte: color})
DISENOS_LISTOS = [
    ("mono-azul-marino-clasico", "Azul marino clásico", un_color("Azul marino")),
    ("mono-guinda-clasico", "Guinda clásico", un_color("Guinda")),
    ("mono-verde-oscuro-clasico", "Verde oscuro clásico", un_color("Verde botella")),
    ("mono-gris-con-blanco", "Gris con blanco", dos_colores("Gris Oxford", "Blanco")),
    ("mono-azul-cielo-con-gris", "Azul cielo con gris", dos_colores("Celeste", "Gris Oxford")),
    ("mono-amarillo-con-azul-marino", "Amarillo con azul marino", dos_colores("Amarillo oro", "Azul marino")),
    ("mono-rojo-con-azul-marino", "Rojo con azul marino", dos_colores("Rojo navidad", "Azul marino")),
    ("mono-rojo-blanco-azul-marino", "Rojo, blanco y azul marino",
     {"basearriba": "Rojo navidad", "patas": "Rojo navidad", "nudo": "Rojo navidad",
      "baseabajo": "Blanco", "tiras": "Blanco", "decorado": "Azul marino"}),
]

# ---------------------------------------------------------------------------
# Listones estampados para el decorado (fotos en static/simulador/estampados/<clave>.jpg).
# Cada diseño puede venir en varios colores; en la página se muestra una punta de
# listón por diseño y, al elegirla, sus colores. Para agregar un color a un diseño
# basta con un renglón aquí y la foto del listón.
# (diseño, grupo, [(color, clave, código del circulito), ...])
# Si el diseño tiene un solo color, el color y el código van vacíos.
# ---------------------------------------------------------------------------
PRECIO_ESTAMPADO = "15.00"   # precio provisional, igual para todos los estampados

DISENOS_ESTAMPADOS = [
    # Escolares
    ("Útiles escolares", Estampado.ESCOLAR, [
        ("Gris", "utiles-gris", "#5E6268"), ("Azul marino", "utiles-azul-marino", "#1C2541"),
        ("Guinda", "utiles-guinda", "#6E1428"), ("Verde botella", "utiles-verde-botella", "#0F4D32"),
        ("Rojo", "utiles-rojo", "#B3122E"), ("Negro", "utiles-negro", "#1A1A1A"),
    ]),
    ("Rejilla", Estampado.ESCOLAR, [
        ("Gris", "rejilla-gris", "#5E6268"), ("Azul marino", "rejilla-azul-marino", "#1C2541"),
        ("Guinda", "rejilla-guinda", "#6E1428"), ("Verde botella", "rejilla-verde-botella", "#0F4D32"),
        ("Rojo", "rejilla-rojo", "#B3122E"), ("Negro", "rejilla-negro", "#1A1A1A"),
    ]),
    ("Rombos", Estampado.ESCOLAR, [
        ("Gris", "rombos-gris", "#5E6268"), ("Azul marino", "rombos-azul-marino", "#1C2541"),
        ("Guinda", "rombos-guinda", "#6E1428"), ("Verde botella", "rombos-verde-botella", "#0F4D32"),
        ("Rosa", "rombos-rosa", "#F4A3B6"), ("Negro", "rombos-negro", "#1A1A1A"),
    ]),
    ("Puntos", Estampado.ESCOLAR, [
        ("Azul marino", "puntos-azul-marino", "#1C2541"), ("Guinda", "puntos-guinda", "#6E1428"),
        ("Verde botella", "puntos-verde-botella", "#0F4D32"), ("Gris", "puntos-gris", "#5E6268"),
        ("Negro", "puntos-negro", "#1A1A1A"), ("Rojo", "puntos-rojo", "#B3122E"),
    ]),
    ("Cuadros con fresas", Estampado.ESCOLAR, [
        ("Turquesa", "cuadros-turquesa", "#2BB3B1"), ("Rosa", "cuadros-rosa", "#F4A3B6"),
        ("Lila", "cuadros-lila", "#A98BD3"), ("Azul rey", "cuadros-azul-rey", "#1F4FB4"),
        ("Verde", "cuadros-verde", "#2E8B3E"),
    ]),
    ("Calado", Estampado.ESCOLAR, [
        ("Rojo", "calado-rojo", "#B3122E"), ("Azul marino", "calado-azul-marino", "#1C2541"),
        ("Guinda", "calado-guinda", "#6E1428"), ("Verde botella", "calado-verde-botella", "#0F4D32"),
        ("Rosa", "calado-rosa", "#F4A3B6"), ("Blanco", "calado-blanco", "#EDEDEA"),
    ]),
    # Navideños
    ("Muñecos de nieve", Estampado.NAVIDENO, [
        ("Azul marino", "nieve-azul-marino", "#1C2541"), ("Rojo", "nieve-rojo", "#B3122E"),
        ("Verde pino", "nieve-verde-pino", "#1F5E3A"), ("Vino", "nieve-vino", "#6B1E2E"),
        ("Gris", "nieve-gris", "#5E6268"), ("Negro", "nieve-negro", "#1A1A1A"),
    ]),
    ("Muñecos de nieve café", Estampado.NAVIDENO, [("", "nieve-cafe", "")]),
    ("Metálico", Estampado.NAVIDENO, [
        ("Plateado", "metalico-plateado", "#C9CCD1"), ("Dorado", "metalico-dorado", "#D4AF37"),
        ("Cobre", "metalico-cobre", "#B87333"), ("Rosa metalico", "metalico-rosa-metalico", "#E3A1B6"),
    ]),
    ("Organza con rayas", Estampado.NAVIDENO, [
        ("Negro", "rayas-negro", "#1A1A1A"), ("Azul marino", "rayas-azul-marino", "#1C2541"),
        ("Rojo", "rayas-rojo", "#B3122E"), ("Verde pino", "rayas-verde-pino", "#1F5E3A"),
        ("Morado", "rayas-morado", "#5B2C83"), ("Guinda", "rayas-guinda", "#6E1428"),
    ]),
    ("Tejido rojo", Estampado.NAVIDENO, [("", "tejido-rojo", "")]),
    ("Rombos verde", Estampado.NAVIDENO, [("", "rombos-verde", "")]),
    # Otros
    ("Mariposas", Estampado.OTRO, [
        ("Rojo", "mariposas-rojo", "#B3122E"), ("Azul marino", "mariposas-azul-marino", "#1C2541"),
        ("Rosa", "mariposas-rosa", "#E58FA8"), ("Lila", "mariposas-lila", "#9C7CC9"),
        ("Verde", "mariposas-verde", "#1F5E3A"), ("Turquesa", "mariposas-turquesa", "#1E9E9C"),
        ("Negro", "mariposas-negro", "#1A1A1A"), ("Dorado", "mariposas-dorado", "#B8902A"),
    ]),
    ("Lunares", Estampado.OTRO, [
        ("Rojo", "lunares-rojo", "#B3122E"), ("Azul marino", "lunares-azul-marino", "#1C2541"),
        ("Rosa mexicano", "lunares-rosa-mexicano", "#E4007C"), ("Verde", "lunares-verde", "#2E8B3E"),
        ("Negro", "lunares-negro", "#1A1A1A"), ("Celeste", "lunares-celeste", "#8EC1E6"),
    ]),
    ("Tul brillante", Estampado.OTRO, [
        ("Celeste", "tul-celeste", "#8EC1E6"), ("Rosa", "tul-rosa", "#F4A3B6"),
        ("Lila", "tul-lila", "#A98BD3"), ("Blanco", "tul-blanco", "#EDEDEA"),
        ("Menta", "tul-menta", "#8FD9C0"), ("Rojo", "tul-rojo", "#B3122E"),
    ]),
    ("Degradado con brillo", Estampado.OTRO, [
        ("Rosa", "rosa-brillo-rosa", "#F4A3B6"), ("Celeste", "rosa-brillo-celeste", "#8EC1E6"),
        ("Lila", "rosa-brillo-lila", "#A98BD3"), ("Rojo", "rosa-brillo-rojo", "#B3122E"),
        ("Menta", "rosa-brillo-menta", "#8FD9C0"), ("Azul rey", "rosa-brillo-azul-rey", "#1F4FB4"),
    ]),
    ("Unicornios", Estampado.OTRO, [("", "unicornios", "")]),
    ("Catarinas", Estampado.OTRO, [("", "catarinas", "")]),
]

# Lista plana (nombre completo, clave, precio), útil para recorrer todos los estampados.
ESTAMPADOS = [
    (f"{diseno} {color.lower()}" if color else diseno, clave, PRECIO_ESTAMPADO)
    for diseno, _grupo, variantes in DISENOS_ESTAMPADOS
    for color, clave, _hex in variantes
]

# ---------------------------------------------------------------------------
# Calcetines (los dio de alta Kevin en el admin el 08/11/2026; aquí quedan fijos
# para que salgan igual en todas las computadoras, en las pruebas y en Render).
# Cada uno es unitalla y de un color. Su foto: static/img/calcetines/<slug>.webp
# ---------------------------------------------------------------------------
DESCRIPCION_CALCETINES_AFELPADOS = """¡Llegó la Navidad a tus Pies! 🎄🧦
Abriga tus días festivos con nuestras calcetas navideñas afelpadas. Diseñadas con interiores \
ultrasuaves y térmicos que mantendrán tus pies calientitos y cómodos durante toda la temporada.

Súper suaves y afelpadas: Tejido exterior de alta calidad con forro interno térmico tipo peluche.

Diseño Unisex y Unitalla: Ajuste cómodo y elástico perfecto tanto para hombres como para mujeres."""

DESCRIPCION_CALCETINES_ALGODON = """¡Llegó la Navidad a tus Pies! 🎄🧦
Abriga tus días festivos con nuestras calcetas navideñas de algodón. Diseñadas con fibras \
naturales de alta calidad y un interior ultrasuave que mantendrá tus pies calientes, frescos y \
cómodos durante toda la temporada.

Algodón Premium: Exterior de algodón transpirable y resistente para máxima comodidad.

Diseño Unisex y Unitalla: Ajuste cómodo, elástico y adaptable, perfecto tanto para hombres como para mujeres."""

AFELPADOS, ALGODON = DESCRIPCION_CALCETINES_AFELPADOS, DESCRIPCION_CALCETINES_ALGODON

# (slug, nombre, precio, precio anterior, color, existencias, días de elaboración, destacado, descripción)
CALCETINES = [
    ("calcetines-santa-claus", "Calcetines Santa Claus",
     "110.00", "130.00", "Rojo navidad", 10, 5, True, AFELPADOS),
    ("calcetines-muneco-de-nieve", "Calcetines Muñeco de Nieve",
     "90.00", "110.00", "Verde navidad", 4, 5, False, AFELPADOS),
    ("calcetines-renos-de-santa", "Calcetines Renos de Santa",
     "90.00", "110.00", "Rojo navidad", 20, 5, False, AFELPADOS),
    ("calcetines-rodolfo-el-reno", "Calcetines Rodolfo el Reno",
     "110.00", "130.00", "Blanco", 20, 5, True, AFELPADOS),
    ("calcetines-hombre-de-galleta", "Calcetines Hombre de Galleta",
     "90.00", "110.00", "Rojo navidad", 30, 5, False, AFELPADOS),
    ("calcetines-muneco-de-nieve-completo", "Calcetines Muñeco de Nieve Completo",
     "110.00", "130.00", "Blanco", 10, 5, True, AFELPADOS),
    ("calcetines-renos-de-santa-algodon-crema", "Calcetines Renos de Santa algodón crema",
     "60.00", "75.00", "Crema", 20, 3, True, ALGODON),
    ("calcetines-renos-de-santa-algodon-negros", "Calcetines Renos de Santa algodón negros",
     "60.00", "75.00", "Negro", 15, 3, True, ALGODON),
]
# Calcetines de ejemplo de la primera versión: dejan de mostrarse.
CALCETINES_RETIRADOS = ["calcetines-rayas", "calcetines-santa"]

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
                "precio_base": Decimal("85.00"),
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

        # --- Estampados (ver DISENOS_ESTAMPADOS) ---
        orden = 0
        for diseno, grupo, variantes in DISENOS_ESTAMPADOS:
            for color, clave, codigo in variantes:
                est, _ = Estampado.objects.update_or_create(
                    clave=clave,
                    defaults={
                        "nombre": f"{diseno} {color.lower()}" if color else diseno,
                        "diseno": diseno, "grupo": grupo,
                        "color_nombre": color, "color_hex": codigo,
                        "precio_extra": Decimal(PRECIO_ESTAMPADO), "orden": orden, "activo": True,
                    },
                )
                est.productos.add(clasico)
                orden += 1
        # Los estampados que ya no están en la lista dejan de mostrarse.
        Estampado.objects.exclude(clave__in=[e[1] for e in ESTAMPADOS]).update(activo=False)

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

        # --- Diseños listos para usar (moños de uniforme, ver DISENOS_LISTOS) ---
        # El "Moño escolar" de la versión anterior deja de mostrarse.
        Producto.objects.filter(slug="mono-escolar").update(activo=False, destacado=False)
        for slug, nombre, por_parte in DISENOS_LISTOS:
            # Colores del diseño sin repetir, para la descripción: "celeste y gris oxford".
            usados = [c.lower() for c in dict.fromkeys(por_parte.values())]
            lista_colores = usados[0] if len(usados) == 1 else ", ".join(usados[:-1]) + " y " + usados[-1]
            # En el carrito y los pedidos se lee "Moño azul marino clásico".
            nombre_producto = f"Moño {nombre[0].lower()}{nombre[1:]}"
            p = self._producto(slug, cats["monos"], nombre_producto, PRECIO_DISENO_LISTO, 0,
                               f"Moño listo para usar, en colores de uniforme: {lista_colores}. "
                               "Se envía tal cual, sin pasar por el simulador.")
            # Una sola variante sin color: el diseño ya trae sus colores.
            # Así la página del producto no muestra un selector de color.
            Variante.objects.update_or_create(
                producto=p, talla="UNI", color=None,
                defaults={"sku": f"ML-{slug.upper()}"[:40], "existencias": 15, "activa": True},
            )
            p.variantes.exclude(talla="UNI", color=None).delete()

        # --- Suéteres (un producto por diseño, en tallas de niña y adulto) ---
        Producto.objects.filter(slug__in=SUETERES_RETIRADOS).update(activo=False, destacado=False)
        for slug, nombre, precio, color, desc in SUETERES:
            p = self._producto(slug, cats["sueteres"], nombre, precio, 0, desc,
                               destacado=slug == "sueter-renos-azul")
            p.variantes.exclude(color=colores[color]).delete()
            for t in TALLAS_NINA:
                # Ejemplo de talla agotada: 10-12 del Suéter Osito.
                stock = 0 if (slug == "sueter-osito" and t == "10-12") else 6
                self._variante(p, t, colores[color], stock)
            for t in TALLAS_ADULTO:
                extra = "40.00" if t == "G" else "0"  # la talla G cuesta $40 más
                self._variante(p, t, colores[color], 4, extra)

        # --- Calcetines (ver CALCETINES arriba) ---
        Producto.objects.filter(slug__in=CALCETINES_RETIRADOS).update(activo=False, destacado=False)
        for slug, nombre, precio, anterior, color, existencias, dias, destacado, desc in CALCETINES:
            p = self._producto(slug, cats["calcetines"], nombre, precio, dias, desc, destacado=destacado)
            p.precio_anterior = Decimal(anterior)   # precio tachado y etiqueta "Ahorra $..."
            # La foto sale de static/img/calcetines/<slug>.webp. Se quita la que se haya
            # subido en el admin (media/), porque esa no se publica en Render.
            p.imagen = ""
            p.save(update_fields=["precio_anterior", "imagen"])
            # Unitalla y un solo color. El SKU lleva el slug completo (sin "calcetines-")
            # para que no choque con el de los calcetines de ejemplo anteriores.
            p.variantes.exclude(talla="UNI", color=colores[color]).delete()
            Variante.objects.update_or_create(
                producto=p, talla="UNI", color=colores[color],
                defaults={"sku": f"CAL-{slug.removeprefix('calcetines-').upper()}"[:40],
                          "existencias": existencias, "precio_extra": Decimal("0")},
            )

        # --- Kits navideños (se venden como un producto con precio de paquete) ---
        for slug, nombre, precio, anterior, color, desc in KITS:
            p = self._producto(slug, cats["kits"], nombre, precio, 3, desc,
                               destacado=slug != "kit-escolar")  # los destacados salen en la portada
            p.precio_anterior = Decimal(anterior)
            p.save(update_fields=["precio_anterior"])
            p.variantes.exclude(color=colores[color]).delete()
            self._variante(p, "UNI", colores[color], 8)

        # --- Guía de tallas y temporada de ejemplo ---
        cats["sueteres"].guia_tallas = GUIA_TALLAS_SUETERES
        cats["sueteres"].save(update_fields=["guia_tallas"])

        temporada, _ = Temporada.objects.update_or_create(
            slug="navidad-2026",
            defaults={
                "nombre": "Navidad 2026",
                "activa": True,
                "aviso": "Esta temporada, el pretexto es Navidad. Envíos a todo México.",
                "etiqueta": "Temporada navideña",
                "titulo": "Este año, el pretexto es Navidad.",
                "descripcion": "Diseña su moño con fotos reales y completa el look con suéter y calcetines a juego.",
                "producto_principal": clasico,
                "boton_texto": "Diseñar mi moño",
            },
        )
        temporada.productos.set(Producto.objects.filter(
            activo=True, categoria__slug__in=["monos", "sueteres", "kits"],
        ).exclude(slug__in=["mono-escolar", "kit-escolar"] + [d[0] for d in DISENOS_LISTOS]))

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
