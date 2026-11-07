"""
Administración de pedidos.

El equipo usa este panel para simular el envío: captura transportista, guía y teléfono,
y avanza el estado. El menú de estado solo ofrece los cambios permitidos, y cada cambio
pasa por servicios.py, igual que si viniera de la tienda.
"""
import secrets

from django import forms
from django.contrib import admin, messages

from . import servicios
from .models import (
    ConfiguracionTienda, EventoPago, EventoPedido, LineaPedido, Pedido, SolicitudPosventa,
)

Estado = Pedido.Estado


class SoloLectura:
    """Los registros históricos no se editan a mano."""

    can_delete = False
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class LineaPedidoInline(SoloLectura, admin.TabularInline):
    model = LineaPedido
    fields = readonly_fields = ["nombre", "seleccion", "cantidad", "precio_unitario"]


class EventoPedidoInline(SoloLectura, admin.TabularInline):
    model = EventoPedido
    fields = readonly_fields = ["estado", "nota", "creado"]


class SolicitudInline(SoloLectura, admin.TabularInline):
    model = SolicitudPosventa
    fields = readonly_fields = ["tipo", "motivo", "estado", "respuesta", "creada"]


class PedidoAdminForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        actual = Estado(self.instance.estado)
        permitidos = [actual, *Pedido.TRANSICIONES[actual]]
        self.fields["estado"].choices = [(e.value, e.label) for e in permitidos]

    def clean(self):
        datos = super().clean()
        if datos.get("estado") in (Estado.ENVIADO, Estado.EN_CAMINO):
            for campo in ("transportista", "numero_guia"):
                if not datos.get(campo):
                    self.add_error(campo, "Es obligatorio para marcar el pedido como enviado.")
        return datos


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    form = PedidoAdminForm
    list_display = ["folio", "usuario", "estado", "total", "transportista", "entrega_maxima", "creado"]
    list_filter = ["estado", "creado"]
    search_fields = ["folio", "usuario__email", "numero_guia", "nombre_destinatario"]
    date_hierarchy = "creado"
    inlines = [LineaPedidoInline, EventoPedidoInline, SolicitudInline]
    actions = ["avanzar", "asignar_transportista_demo"]
    readonly_fields = [
        "folio", "usuario", "subtotal", "costo_envio", "total", "entrega_minima", "entrega_maxima",
        "nombre_destinatario", "telefono", "calle", "colonia", "codigo_postal", "ciudad",
        "entidad", "referencias", "sesion_pago", "referencia_pago", "pagado_en", "creado",
    ]
    fieldsets = [
        ("Pedido", {"fields": ["folio", "usuario", "estado", "creado"]}),
        ("Envío", {"fields": [
            "transportista", "numero_guia", "telefono_transportista", "entrega_minima", "entrega_maxima",
        ]}),
        ("Dirección de entrega", {"fields": [
            "nombre_destinatario", "telefono", "calle", "colonia", "codigo_postal",
            "ciudad", "entidad", "referencias",
        ]}),
        ("Importes y pago", {"fields": [
            "subtotal", "costo_envio", "total", "sesion_pago", "referencia_pago", "pagado_en",
        ]}),
    ]

    def has_add_permission(self, request):
        return False  # los pedidos solo nacen de una compra

    def has_delete_permission(self, request, obj=None):
        return False  # se cancelan, no se borran

    def save_model(self, request, obj, form, change):
        """Guarda los datos del envío y aplica el cambio de estado con sus reglas."""
        nuevo = form.cleaned_data["estado"]
        obj.estado = Pedido.objects.values_list("estado", flat=True).get(pk=obj.pk)
        obj.save()
        if nuevo != obj.estado:
            try:
                servicios.cambiar_estado(obj, nuevo, f"Actualizado por {request.user.get_username()}.")
            except servicios.ErrorPedido as e:
                self.message_user(request, str(e), messages.ERROR)

    @admin.action(description="Avanzar al siguiente estado")
    def avanzar(self, request, queryset):
        for pedido in queryset:
            siguientes = [e for e in Pedido.TRANSICIONES[Estado(pedido.estado)] if e in Pedido.PASOS]
            try:
                if not siguientes:
                    raise servicios.ErrorPedido("ya no tiene un siguiente estado.")
                servicios.cambiar_estado(pedido, siguientes[0], f"Actualizado por {request.user.get_username()}.")
            except servicios.ErrorPedido as e:
                self.message_user(request, f"{pedido.folio}: {e}", messages.WARNING)
            else:
                self.message_user(request, f"{pedido.folio}: {siguientes[0].label}.", messages.SUCCESS)

    @admin.action(description="Asignar transportista de prueba")
    def asignar_transportista_demo(self, request, queryset):
        for pedido in queryset:
            pedido.transportista = pedido.transportista or "Paquetería Demo"
            pedido.numero_guia = pedido.numero_guia or f"DEMO-{secrets.token_hex(4).upper()}"
            pedido.telefono_transportista = pedido.telefono_transportista or "5511111111"
            pedido.save(update_fields=[
                "transportista", "numero_guia", "telefono_transportista", "actualizado",
            ])
        self.message_user(request, "Transportista de prueba asignado.", messages.SUCCESS)


@admin.register(SolicitudPosventa)
class SolicitudPosventaAdmin(admin.ModelAdmin):
    list_display = ["pedido", "tipo", "estado", "creada", "resuelta"]
    list_filter = ["tipo", "estado"]
    search_fields = ["pedido__folio", "motivo"]
    readonly_fields = ["pedido", "tipo", "motivo", "estado", "creada", "resuelta"]
    actions = ["aprobar", "rechazar"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def _resolver(self, request, queryset, aprobar, respuesta):
        for solicitud in queryset:
            try:
                servicios.resolver_solicitud(solicitud, aprobar, solicitud.respuesta or respuesta)
            except servicios.ErrorPedido as e:
                self.message_user(request, f"{solicitud.pedido.folio}: {e}", messages.ERROR)
            else:
                self.message_user(request, f"{solicitud.pedido.folio}: solicitud resuelta.", messages.SUCCESS)

    @admin.action(description="Aprobar las solicitudes elegidas")
    def aprobar(self, request, queryset):
        self._resolver(request, queryset, True, "Tu solicitud fue aprobada.")

    @admin.action(description="Rechazar las solicitudes elegidas")
    def rechazar(self, request, queryset):
        self._resolver(request, queryset, False, "Tu solicitud no pudo aprobarse.")


@admin.register(ConfiguracionTienda)
class ConfiguracionTiendaAdmin(admin.ModelAdmin):
    list_display = ["__str__", "costo_envio", "telefono_soporte", "whatsapp"]

    def has_add_permission(self, request):
        return not ConfiguracionTienda.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EventoPago)
class EventoPagoAdmin(admin.ModelAdmin):
    list_display = ["evento_id", "tipo", "recibido"]
    search_fields = ["evento_id"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
