"""
Modelos del catálogo.

Categoria   -> Moños, Suéteres navideños, Calcetines.
Producto    -> lo que se muestra en el catálogo (precio base y días de elaboración).
Variante    -> combinación vendible con existencias (talla y/o color). La usan los
               productos de catálogo: suéteres, calcetines y el moño "tal cual".
Color       -> paleta de colores de listón disponible para el simulador.
Parte       -> capa del moño personalizable (lazos, nudo, colas...). Cada parte
               tiene su PNG y la lista de colores permitidos.
Decoracion  -> extra opcional del moño (perla, cascabel, copo) con costo adicional.
"""
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse

validador_hex = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="Usa el formato #RRGGBB, por ejemplo #C1121F.",
)


class Categoria(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:categoria", args=[self.slug])


class Color(models.Model):
    nombre = models.CharField(max_length=40, unique=True)
    codigo_hex = models.CharField(max_length=7, validators=[validador_hex])
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name_plural = "colores"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="productos"
    )
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    precio_base = models.DecimalField(
        max_digits=8, decimal_places=2, validators=[MinValueValidator(0)]
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
    destacado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["categoria__orden", "nombre"]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:producto", args=[self.slug])

    @property
    def existencias_totales(self):
        return sum(v.existencias for v in self.variantes.filter(activa=True))

    @property
    def disponible(self):
        if not self.activo:
            return False
        if self.personalizable:
            return True  # se elabora sobre pedido
        return self.existencias_totales > 0


class Variante(models.Model):
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
    sku = models.CharField(max_length=40, unique=True)
    existencias = models.PositiveIntegerField(default=0)
    precio_extra = models.DecimalField(
        max_digits=8, decimal_places=2, default=0,
        help_text="Se suma al precio base (por ejemplo, tallas grandes).",
    )
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["producto", "id"]  # en el orden en que se dieron de alta
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "talla", "color"], name="variante_unica"
            )
        ]

    def __str__(self):
        partes = [self.producto.nombre, self.get_talla_display()]
        if self.color:
            partes.append(self.color.nombre)
        return " / ".join(partes)

    @property
    def precio(self):
        return self.producto.precio_base + self.precio_extra


class Parte(models.Model):
    """Capa recoloreable del moño personalizable."""

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="partes",
        limit_choices_to={"personalizable": True},
    )
    clave = models.SlugField(
        max_length=30, help_text="Identificador corto: lazos, nudo, colas..."
    )
    nombre = models.CharField(max_length=40)
    orden = models.PositiveSmallIntegerField(
        default=0, help_text="Orden de dibujo: primero el fondo, al final lo de enfrente."
    )
    imagen_capa = models.ImageField(
        upload_to="capas/", blank=True,
        help_text="PNG en tonos claros con fondo transparente.",
    )
    colores = models.ManyToManyField(Color, related_name="partes")
    color_inicial = models.ForeignKey(
        Color, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["producto", "orden"]
        constraints = [
            models.UniqueConstraint(fields=["producto", "clave"], name="parte_unica")
        ]

    def __str__(self):
        return f"{self.producto.nombre} – {self.nombre}"


class Decoracion(models.Model):
    """Extra opcional (perla, cascabel, copo). Su imagen NO se recolorea."""

    productos = models.ManyToManyField(
        Producto,
        related_name="decoraciones",
        limit_choices_to={"personalizable": True},
    )
    nombre = models.CharField(max_length=40)
    clave = models.SlugField(max_length=30, unique=True)
    precio_extra = models.DecimalField(
        max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    dias_extra = models.PositiveSmallIntegerField(default=0)
    imagen = models.ImageField(upload_to="decoraciones/", blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "decoración"
        verbose_name_plural = "decoraciones"

    def __str__(self):
        return f"{self.nombre} (+${self.precio_extra})"
