"""
Modelos de compra y seguimiento.

ConfiguracionTienda -> datos que el equipo cambia desde el admin: envío y soporte.
Pedido              -> compra de un cliente: dirección, importes, estado y envío.
LineaPedido         -> copia de lo comprado. Conserva precio y personalización aunque
                       después cambie el catálogo.
EventoPedido        -> historial de estados; con él se dibuja la línea de tiempo.
EventoPago          -> avisos ya procesados de Stripe, para no aplicar dos veces un pago.
SolicitudPosventa   -> solicitud de cancelación o devolución del cliente.
"""
import secrets
from urllib.parse import quote

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse

PREFIJO_FOLIO = "PR-"
# Sin 0, O, 1, I ni L para que el folio se pueda dictar por teléfono sin confusión.
ALFABETO_FOLIO = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

validador_telefono = RegexValidator(r"^\d{10}$", "Escribe 10 dígitos, sin espacios ni guiones.")
validador_cp = RegexValidator(r"^\d{5}$", "El código postal tiene 5 dígitos.")


def generar_folio():
    """Folio público no consecutivo: no revela cuántas ventas hay ni permite adivinar otros."""
    return PREFIJO_FOLIO + "".join(secrets.choice(ALFABETO_FOLIO) for _ in range(8))


class ConfiguracionTienda(models.Model):
    """Una sola fila con los datos que se editan sin programar."""

    costo_envio = models.DecimalField(
        "costo de envío", max_digits=8, decimal_places=2, default=99,
        validators=[MinValueValidator(0)], help_text="Tarifa fija para todo México.",
    )
    telefono_soporte = models.CharField(
        "teléfono de soporte", max_length=10, default="5500000000", validators=[validador_telefono],
        help_text="Número ficticio de ejemplo; cámbialo por el real al presentar.",
    )
    whatsapp = models.CharField(
        "WhatsApp de soporte", max_length=10, default="5500000000", validators=[validador_telefono],
        help_text="10 dígitos. Número ficticio de ejemplo; cámbialo por el real al presentar.",
    )
    horario_soporte = models.CharField(
        "horario de soporte", max_length=80, default="Lunes a viernes de 9:00 a 18:00",
    )

    class Meta:
        verbose_name = "configuración de la tienda"
        verbose_name_plural = "configuración de la tienda"

    def __str__(self):
        return "Configuración de la tienda"

    def save(self, *args, **kwargs):
        self.pk = 1  # siempre la misma fila
        super().save(*args, **kwargs)

    @classmethod
    def cargar(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def enlace_whatsapp(self, mensaje=None):
        """Enlace que abre WhatsApp con el mensaje ya escrito (52 es la lada de México)."""
        mensaje = mensaje or f"Hola, necesito ayuda con la tienda {settings.NOMBRE_TIENDA}."
        return f"https://wa.me/52{self.whatsapp}?text={quote(mensaje)}"


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE_PAGO = "pendiente_pago", "Pendiente de pago"
        CONFIRMADO = "confirmado", "Confirmado"
        EN_PREPARACION = "en_preparacion", "En preparación"
        ENVIADO = "enviado", "Enviado"
        EN_CAMINO = "en_camino", "En camino"
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"
        DEVUELTO = "devuelto", "Devuelto"

    # Cambios de estado permitidos. Cualquier otro se rechaza.
    TRANSICIONES = {
        Estado.PENDIENTE_PAGO: (Estado.CONFIRMADO, Estado.CANCELADO),
        Estado.CONFIRMADO: (Estado.EN_PREPARACION, Estado.CANCELADO),
        Estado.EN_PREPARACION: (Estado.ENVIADO,),
        Estado.ENVIADO: (Estado.EN_CAMINO,),
        Estado.EN_CAMINO: (Estado.ENTREGADO,),
        Estado.ENTREGADO: (Estado.DEVUELTO,),
        Estado.CANCELADO: (),
        Estado.DEVUELTO: (),
    }
    # Pasos que ve el cliente en la línea de tiempo.
    PASOS = (
        Estado.CONFIRMADO, Estado.EN_PREPARACION, Estado.ENVIADO, Estado.EN_CAMINO, Estado.ENTREGADO,
    )

    folio = models.CharField(max_length=12, unique=True, default=generar_folio, editable=False)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos",
    )
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE_PAGO)

    # Dirección de entrega
    nombre_destinatario = models.CharField("nombre de quien recibe", max_length=120)
    telefono = models.CharField("teléfono", max_length=10, validators=[validador_telefono])
    calle = models.CharField("calle y número", max_length=160)
    colonia = models.CharField(max_length=120)
    codigo_postal = models.CharField("código postal", max_length=5, validators=[validador_cp])
    ciudad = models.CharField("ciudad o alcaldía", max_length=120)
    entidad = models.CharField("estado", max_length=60)
    referencias = models.CharField("referencias", max_length=200, blank=True)

    # Importes calculados por el servidor
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    costo_envio = models.DecimalField("costo de envío", max_digits=8, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    entrega_minima = models.DateField("entrega desde")
    entrega_maxima = models.DateField("entrega hasta")

    # Envío (se capturan desde el admin)
    transportista = models.CharField(max_length=80, blank=True)
    numero_guia = models.CharField("número de guía", max_length=40, blank=True)
    telefono_transportista = models.CharField(
        "teléfono del transportista", max_length=10, blank=True, validators=[validador_telefono],
    )

    # Pago
    sesion_pago = models.CharField("sesión de pago", max_length=120, blank=True, db_index=True)
    referencia_pago = models.CharField("referencia de pago", max_length=120, blank=True)
    pagado_en = models.DateTimeField("pagado el", null=True, blank=True)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return self.folio

    def get_absolute_url(self):
        return reverse("pedidos:detalle", args=[self.folio])

    @property
    def esta_pendiente(self):
        return self.estado == self.Estado.PENDIENTE_PAGO

    @property
    def transportista_visible(self):
        """El transportista aparece desde que el paquete sale."""
        return self.estado in (self.Estado.ENVIADO, self.Estado.EN_CAMINO, self.Estado.ENTREGADO)

    @property
    def telefono_transportista_visible(self):
        """El teléfono solo se muestra mientras el paquete va en camino (protege sus datos)."""
        return self.telefono_transportista if self.estado == self.Estado.EN_CAMINO else ""

    @property
    def puede_cancelarse(self):
        """Política de la tienda: sin costo mientras no entre a elaboración."""
        return self.estado == self.Estado.CONFIRMADO

    @property
    def puede_devolverse(self):
        return self.estado == self.Estado.ENTREGADO

    @property
    def solicitud_abierta(self):
        return self.solicitudes.filter(estado=SolicitudPosventa.Estado.SOLICITADA).first()

    @property
    def linea_de_tiempo(self):
        """Pasos para la línea de tiempo: nombre, si ya ocurrió, si es el actual y su fecha."""
        fechas = {e.estado: e.creado for e in self.eventos.all()}
        estado = self.Estado.ENTREGADO if self.estado == self.Estado.DEVUELTO else self.estado
        actual = self.PASOS.index(estado) if estado in self.PASOS else -1
        return [
            {
                "nombre": paso.label,
                "hecho": i <= actual,
                "actual": i == actual,
                "fecha": fechas.get(paso.value),
            }
            for i, paso in enumerate(self.PASOS)
        ]


class LineaPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="lineas")
    producto = models.ForeignKey(
        "catalogo.Producto", on_delete=models.SET_NULL, null=True, related_name="+",
    )
    variante = models.ForeignKey(
        "catalogo.Variante", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    nombre = models.CharField(max_length=100)
    seleccion = models.JSONField(default=dict, help_text="Talla, color o partes del moño, ya legibles.")
    opciones = models.JSONField(default=dict, help_text="Selección original con identificadores.")
    vista_previa = models.TextField(blank=True, help_text="Imagen del moño tal como lo vio el cliente.")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.PositiveSmallIntegerField()

    class Meta:
        verbose_name = "línea del pedido"
        verbose_name_plural = "líneas del pedido"

    def __str__(self):
        return f"{self.cantidad} × {self.nombre}"

    @property
    def importe(self):
        return self.precio_unitario * self.cantidad


class EventoPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="eventos")
    estado = models.CharField(max_length=20, choices=Pedido.Estado.choices)
    nota = models.CharField(max_length=200, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creado", "id"]
        verbose_name = "evento del pedido"
        verbose_name_plural = "eventos del pedido"

    def __str__(self):
        return f"{self.pedido}: {self.get_estado_display()}"


class EventoPago(models.Model):
    """Un aviso de Stripe puede llegar más de una vez; este registro evita repetirlo."""

    evento_id = models.CharField(max_length=120, unique=True)
    tipo = models.CharField(max_length=80)
    recibido = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recibido"]
        verbose_name = "evento de pago"
        verbose_name_plural = "eventos de pago"

    def __str__(self):
        return self.evento_id


class SolicitudPosventa(models.Model):
    class Tipo(models.TextChoices):
        CANCELACION = "cancelacion", "Cancelación"
        DEVOLUCION = "devolucion", "Devolución"

    class Estado(models.TextChoices):
        SOLICITADA = "solicitada", "Solicitada"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="solicitudes")
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    motivo = models.TextField(max_length=500)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.SOLICITADA)
    respuesta = models.CharField(max_length=300, blank=True)
    creada = models.DateTimeField(auto_now_add=True)
    resuelta = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creada"]
        verbose_name = "solicitud de cancelación o devolución"
        verbose_name_plural = "solicitudes de cancelación o devolución"
        constraints = [
            models.UniqueConstraint(
                fields=["pedido"], condition=Q(estado="solicitada"), name="una_solicitud_abierta",
            )
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.pedido}"
