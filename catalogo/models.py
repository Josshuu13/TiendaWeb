"""
Modelos del catálogo (tablas de la base de datos).

Categoria   -> agrupa productos en el menú. Se crean desde el admin.
Producto    -> lo que se muestra en el catálogo (precio base y días de elaboración).
Variante    -> combinación vendible con existencias (talla y/o color). La usan los
               productos de catálogo: suéteres, calcetines y el moño "tal cual".
Color       -> paleta de colores de listón (escolares, navideños y básicos).
Parte       -> capa del moño personalizable: patas, base de abajo, base de arriba,
               decorado, tiras y nudo. Cada parte tiene su imagen (PNG en gris) y
               la lista de colores permitidos.
Estampado   -> listón decorado (cuadros, rombos...) que puede usarse en el decorado
               en lugar de un color liso. Solo necesita UNA foto del listón, recta.
Combinacion -> combinación de colores lista para usar ("Lo más vendido"). Con un
               clic el cliente pinta todas las partes del moño.
Temporada   -> campaña de la portada: textos, imagen, fechas y productos. Cambiar de
               temporada no requiere programar.
"""
import secrets

from django.contrib.staticfiles import finders
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone

# Valida que el color tenga el formato #RRGGBB (por ejemplo #B3122E).
validador_hex = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Usa el formato #RRGGBB, por ejemplo #C1121F.",
)


class Categoria(models.Model):
    """Agrupa productos en el menú (Moños, Suéteres, Calcetines)."""

    nombre = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)  # versión para URL: "sueteres"
    descripcion = models.TextField(blank=True)
    guia_tallas = models.TextField(
        "guía de tallas", blank=True,
        help_text="Opcional. Se muestra en los productos de esta categoría, un dato por renglón.",
    )
    orden = models.PositiveSmallIntegerField(default=0)  # orden en el menú

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:categoria", args=[self.slug])


class Color(models.Model):
    """Color de listón. El simulador tiñe la foto gris con este código hexadecimal."""

    # Grupos para mostrar la paleta ordenada al cliente.
    ESCOLAR = "escolar"
    NAVIDENO = "navideno"
    BASICO = "basico"
    GRUPOS = [
        (ESCOLAR, "Escolares"),
        (NAVIDENO, "Navideños"),
        (BASICO, "Básicos y pastel"),
    ]

    nombre = models.CharField(max_length=40, unique=True)
    codigo_hex = models.CharField(max_length=7, validators=[validador_hex])
    grupo = models.CharField(max_length=10, choices=GRUPOS, default=BASICO)
    activo = models.BooleanField(default=True)  # se puede ocultar sin borrarlo
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name_plural = "colores"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Producto del catálogo. Si es personalizable, se vende desde el simulador."""

    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="productos"
    )
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    precio_base = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
    )
    precio_anterior = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Opcional. Precio sin descuento; se muestra tachado (útil para los kits).",
    )
    dias_elaboracion = models.PositiveSmallIntegerField(
        default=0,
        help_text="Días hábiles para preparar el producto antes de enviarlo.",
    )
    personalizable = models.BooleanField(
        default=False,
        help_text="Si está marcado, se vende desde el simulador (sin variantes).",
    )
    imagen = models.ImageField(upload_to="productos/", blank=True)
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)  # aparece en la portada
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["categoria__orden", "nombre"]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:producto", args=[self.slug])

    @property
    def existencias_totales(self):
        """Suma de existencias de todas sus variantes activas."""
        return sum(v.existencias for v in self.variantes.filter(activa=True))

    @property
    def disponible(self):
        """¿Se puede vender? Los personalizables siempre, porque se hacen sobre pedido."""
        if not self.activo:
            return False
        if self.personalizable:
            return True
        return self.existencias_totales > 0

    @property
    def ahorro(self):
        """Cuánto se ahorra respecto al precio anterior (0 si no hay descuento)."""
        if self.precio_anterior and self.precio_anterior > self.precio_base:
            return self.precio_anterior - self.precio_base
        return 0

    @property
    def colores_disponibles(self):
        """Colores distintos de sus variantes activas (para los puntitos y el selector)."""
        vistos, colores = set(), []
        for v in self.variantes.all():
            if v.activa and v.color_id and v.color_id not in vistos:
                vistos.add(v.color_id)
                colores.append(v.color)
        return colores

    @property
    def color_muestra(self):
        """Color con el que se dibuja el producto mientras no tenga foto."""
        colores = self.colores_disponibles
        return colores[0].codigo_hex if colores else "#B3122E"

    @property
    def url_imagen_estatica(self):
        """Imagen guardada en el repositorio: static/img/<categoria>/<slug>.webp.

        Devuelve "" si no existe, y entonces se usa el dibujo de ejemplo.
        """
        ruta = f"img/{self.categoria.slug}/{self.slug}.webp"
        return static(ruta) if finders.find(ruta) else ""

    @property
    def carpeta_simulador(self):
        """Carpeta de archivos estáticos con las capas del simulador de este producto."""
        return f"simulador/{self.slug}/"


class Variante(models.Model):
    """Pieza concreta con existencias: por ejemplo, Suéter Reno, talla M, rojo."""

    TALLAS = [
        ("UNI", "Unitalla"),
        ("CH", "Chica"),
        ("M", "Mediana"),
        ("G", "Grande"),
        ("EG", "Extra grande"),
        ("2-4", "Niña 2-4"),
        ("6-8", "Niña 6-8"),
        ("10-12", "Niña 10-12"),
    ]

    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE, related_name="variantes"
    )
    talla = models.CharField(max_length=5, choices=TALLAS, default="UNI")
    color = models.ForeignKey(
        Color, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    sku = models.CharField(
        max_length=40, unique=True, null=True, blank=True,
        help_text="Código único de inventario. Si lo dejas vacío, se genera solo.",
    )
    existencias = models.PositiveIntegerField(default=0)
    precio_extra = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Se suma al precio base (por ejemplo, tallas grandes).",
    )
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["producto", "id"]  # en el orden en que se dieron de alta
        constraints = [
            # No puede haber dos variantes iguales del mismo producto.
            models.UniqueConstraint(
                fields=["producto", "talla", "color"], name="variante_unica"
            )
        ]

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = self._generar_sku()
        super().save(*args, **kwargs)

    def _generar_sku(self):
        """Arma el código con producto, talla y color; agrega azar si ya existe."""
        color = "".join(p[:3] for p in self.color.nombre.split()).upper() if self.color else "STD"
        sku = f"{self.producto.slug.upper()[:20]}-{self.talla}-{color}"
        if Variante.objects.filter(sku=sku).exists():
            sku = f"{sku}-{secrets.token_hex(2).upper()}"
        return sku

    def __str__(self):
        partes = [self.producto.nombre, self.get_talla_display()]
        if self.color:
            partes.append(self.color.nombre)
        return " / ".join(partes)

    @property
    def precio(self):
        return self.producto.precio_base + self.precio_extra


class Parte(models.Model):
    """
    Capa recoloreable del moño personalizable.

    Las capas se dibujan en el orden del campo `orden` (primero lo de atrás).
    Todas las imágenes deben medir lo mismo para encajar una sobre otra.
    """

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="partes",
        limit_choices_to={"personalizable": True},
    )
    clave = models.SlugField(
        max_length=30,
        help_text="Identificador corto: patas, baseabajo, basearriba, decorado, tiras, nudo.",
    )
    nombre = models.CharField(max_length=40)  # lo que ve el cliente: "Base de arriba"
    orden = models.PositiveSmallIntegerField(
        default=0, help_text="Orden de dibujo: primero el fondo, al final lo de enfrente."
    )
    imagen_capa = models.ImageField(
        upload_to="capas/", blank=True,
        help_text="PNG en gris con fondo transparente. Si se deja vacío, se usa la "
                  "imagen de static/simulador/<producto>/<clave>.png.",
    )
    colores = models.ManyToManyField(Color, related_name="partes")
    color_inicial = models.ForeignKey(
        Color, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    admite_estampado = models.BooleanField(
        default=False,
        help_text="Si está marcado, el cliente puede elegir un listón estampado "
                  "en lugar de un color liso (se usa en el decorado).",
    )
    paso = models.PositiveSmallIntegerField(
        default=0,
        help_text="Orden en que el cliente elige las partes (paso 1, 2, 3...). "
                  "Puede ser distinto del orden de dibujo.",
    )

    class Meta:
        ordering = ["producto", "orden"]
        constraints = [
            models.UniqueConstraint(fields=["producto", "clave"], name="parte_unica")
        ]

    def __str__(self):
        return f"{self.producto.nombre} – {self.nombre}"

    @property
    def url_capa(self):
        """URL de la imagen de la capa: la subida en el admin o, si no hay, la estática."""
        if self.imagen_capa:
            return self.imagen_capa.url
        return static(f"{self.producto.carpeta_simulador}{self.clave}.png")


class Estampado(models.Model):
    """
    Listón decorado que se "estampa" sobre el decorado del moño.

    La imagen es una foto del listón, recto y vertical, recortada justo a su ancho
    (sin mesa ni fondo). El simulador la repite a lo largo de las colas.
    Los colores del estampado son los reales: no se recolorea.
    """

    productos = models.ManyToManyField(
        Producto,
        related_name="estampados",
        limit_choices_to={"personalizable": True},
    )
    nombre = models.CharField(max_length=60)  # "Tejido rojo"
    clave = models.SlugField(max_length=40, unique=True)  # "tejido-rojo"
    imagen = models.ImageField(
        upload_to="estampados/", blank=True,
        help_text="Foto del listón recto y vertical, recortada a su ancho. Si se deja "
                  "vacío, se usa static/simulador/estampados/<clave>.jpg.",
    )
    precio_extra = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]

    def __str__(self):
        return f"{self.nombre} (+${self.precio_extra})"

    @property
    def url_imagen(self):
        """URL de la tira del estampado: la subida en el admin o la estática."""
        if self.imagen:
            return self.imagen.url
        return static(f"simulador/estampados/{self.clave}.jpg")


class Combinacion(models.Model):
    """
    Combinación de colores lista para usar, que aparece en "Lo más vendido".

    Se arma en el admin: nombre + un color por cada parte del moño (y, si se
    quiere, un estampado para el decorado).
    """

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="combinaciones",
        limit_choices_to={"personalizable": True},
    )
    nombre = models.CharField(max_length=60)  # "Navidad clásica"
    estampado = models.ForeignKey(
        Estampado, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Opcional: si se elige, el decorado usa este estampado.",
    )
    activa = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "combinación (lo más vendido)"
        verbose_name_plural = "combinaciones (lo más vendido)"

    def __str__(self):
        return self.nombre

    def como_dict(self):
        """Datos para el navegador: {clave de parte: id de color} y estampado."""
        return {
            "nombre": self.nombre,
            "colores": {cp.parte.clave: cp.color_id for cp in self.colores.all()},
            "estampado": self.estampado.clave if self.estampado else "",
        }


class CombinacionParte(models.Model):
    """Color de una parte dentro de una combinación (por ejemplo: Patas = Vino)."""

    combinacion = models.ForeignKey(
        Combinacion, on_delete=models.CASCADE, related_name="colores"
    )
    parte = models.ForeignKey(Parte, on_delete=models.CASCADE, related_name="+")
    color = models.ForeignKey(Color, on_delete=models.PROTECT, related_name="+")

    class Meta:
        verbose_name = "color de la combinación"
        verbose_name_plural = "colores de la combinación"
        constraints = [
            models.UniqueConstraint(fields=["combinacion", "parte"], name="combinacion_parte_unica")
        ]

    def __str__(self):
        return f"{self.parte.nombre}: {self.color.nombre}"


class Temporada(models.Model):
    """
    Campaña que se ve en la portada: Navidad, regreso a clases, Día de las Madres...

    Se muestra la primera que esté activa y dentro de sus fechas. Si las fechas se dejan
    vacías, solo depende de la casilla "activa". Con fechas, cada temporada puede
    prepararse antes y entra y sale sola.
    """

    nombre = models.CharField(max_length=60)  # "Navidad 2026"
    slug = models.SlugField(max_length=60, unique=True)
    activa = models.BooleanField(default=False)
    inicio = models.DateField(null=True, blank=True, help_text="Opcional. Primer día en que se muestra.")
    fin = models.DateField(null=True, blank=True, help_text="Opcional. Último día en que se muestra.")
    aviso = models.CharField(
        max_length=140, blank=True, help_text="Texto de la franja superior de todas las páginas.",
    )
    etiqueta = models.CharField(max_length=60, blank=True, help_text="Texto pequeño arriba del título.")
    titulo = models.CharField("título", max_length=90)
    descripcion = models.TextField("descripción", blank=True)
    imagen = models.ImageField(
        upload_to="temporadas/", blank=True,
        help_text="Imagen de la portada. Si se deja vacía, se usa static/img/temporadas/<slug>.webp.",
    )
    producto_principal = models.ForeignKey(
        Producto, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Opcional. Producto al que lleva el botón principal.",
    )
    boton_texto = models.CharField("texto del botón", max_length=40, default="Ver producto")
    productos = models.ManyToManyField(Producto, blank=True, related_name="temporadas")
    orden = models.PositiveSmallIntegerField(default=0, help_text="Si dos coinciden, se muestra la de menor orden.")

    class Meta:
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:temporada", args=[self.slug])

    @classmethod
    def actual(cls):
        """Temporada vigente hoy, o None si no hay ninguna."""
        hoy = timezone.localdate()
        return cls.objects.filter(
            Q(inicio__isnull=True) | Q(inicio__lte=hoy),
            Q(fin__isnull=True) | Q(fin__gte=hoy),
            activa=True,
        ).select_related("producto_principal").first()

    @property
    def url_imagen(self):
        """Imagen subida en el admin o, si no hay, la estática con el nombre del slug."""
        if self.imagen:
            return self.imagen.url
        ruta = f"img/temporadas/{self.slug}.webp"
        return static(ruta) if finders.find(ruta) else ""
