"""
Vistas de compra y seguimiento.

Solo atienden la petición: revisan quién la hace y llaman a servicios.py, donde viven
las reglas. Un cliente nunca ve pedidos ajenos: la búsqueda siempre filtra por usuario
y un folio ajeno responde 404, como si no existiera.
"""
import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from carrito.carrito import Carrito

from . import pagos, servicios
from .forms import DatosEnvioForm, SolicitudForm
from .models import ConfiguracionTienda, Pedido, SolicitudPosventa

logger = logging.getLogger(__name__)


def _pedido_propio(request, folio):
    return get_object_or_404(Pedido, folio=folio, usuario=request.user)


def _datos_previos(usuario):
    """Propone la dirección del último pedido para no volver a escribirla."""
    ultimo = usuario.pedidos.first()
    if ultimo is None:
        return {"nombre_destinatario": usuario.get_full_name() or usuario.first_name}
    return {campo: getattr(ultimo, campo) for campo in DatosEnvioForm.Meta.fields}


def _iniciar_pago(request, pedido):
    """Manda al cliente a Stripe o, en desarrollo sin llaves, al pago simulado."""
    if pagos.stripe_activo():
        url_pedido = request.build_absolute_uri(pedido.get_absolute_url())
        try:
            return redirect(pagos.crear_sesion_checkout(pedido, f"{url_pedido}?pago=ok", url_pedido))
        except stripe.StripeError:
            logger.exception("No se pudo crear el pago de %s", pedido.folio)
            messages.error(request, "No pudimos abrir la página de pago. Intenta de nuevo.")
            return redirect(pedido)
    if settings.PAGO_SIMULADO:
        return redirect("pedidos:pago_simulado", folio=pedido.folio)
    messages.error(request, "Los pagos no están configurados en este momento.")
    return redirect(pedido)


@login_required
def compra(request):
    carrito = Carrito(request.session)
    resumen = carrito.resumen(ConfiguracionTienda.cargar().costo_envio)
    if not resumen.lineas:
        return redirect("carrito:ver")
    if resumen.tiene_errores:
        messages.error(request, "Revisa tu carrito: hay productos que cambiaron.")
        return redirect("carrito:ver")

    form = DatosEnvioForm(request.POST or None, initial=_datos_previos(request.user))
    if request.method == "POST" and form.is_valid():
        try:
            pedido = servicios.crear_pedido(request.user, resumen, form.cleaned_data)
        except servicios.ErrorPedido as e:
            messages.error(request, str(e))
            return redirect("carrito:ver")
        carrito.vaciar()
        return _iniciar_pago(request, pedido)
    return render(request, "pedidos/compra.html", {"form": form, "resumen": resumen})


@login_required
def lista(request):
    pedidos = request.user.pedidos.prefetch_related("lineas")
    return render(request, "pedidos/lista.html", {"pedidos": pedidos})


@login_required
def detalle(request, folio):
    pedido = _pedido_propio(request, folio)
    tipo_solicitud = (
        SolicitudPosventa.Tipo.CANCELACION if pedido.puede_cancelarse else SolicitudPosventa.Tipo.DEVOLUCION
    )
    return render(request, "pedidos/detalle.html", {
        "pedido": pedido,
        "esperando_pago": pedido.esta_pendiente and request.GET.get("pago") == "ok",
        "enlace_whatsapp": ConfiguracionTienda.cargar().enlace_whatsapp(
            f"Hola, necesito ayuda con mi pedido {pedido.folio}."
        ),
        "form_solicitud": SolicitudForm(initial={"tipo": tipo_solicitud}),
    })


@login_required
@require_POST
def pagar(request, folio):
    """Reintento de pago de un pedido que quedó pendiente."""
    pedido = _pedido_propio(request, folio)
    if not pedido.esta_pendiente:
        return redirect(pedido)
    return _iniciar_pago(request, pedido)


@login_required
@require_POST
def descartar(request, folio):
    """El cliente abandona un pedido sin pagar: se liberan las piezas apartadas."""
    pedido = _pedido_propio(request, folio)
    if pedido.esta_pendiente:
        servicios.cambiar_estado(pedido, Pedido.Estado.CANCELADO, "Cancelado por el cliente antes de pagar.")
        messages.success(request, "Cancelamos tu pedido.")
    return redirect(pedido)


@login_required
@require_POST
def solicitud(request, folio):
    pedido = _pedido_propio(request, folio)
    form = SolicitudForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Cuéntanos el motivo de tu solicitud.")
        return redirect(pedido)
    try:
        servicios.crear_solicitud(pedido, form.cleaned_data["tipo"], form.cleaned_data["motivo"])
    except servicios.ErrorPedido as e:
        messages.error(request, str(e))
    else:
        messages.success(request, "Recibimos tu solicitud. Te avisaremos cuando la revisemos.")
    return redirect(pedido)


@login_required
def pago_simulado(request, folio):
    """Pasarela de práctica. Solo existe en desarrollo y sin llaves de Stripe."""
    if not settings.PAGO_SIMULADO:
        raise Http404
    pedido = _pedido_propio(request, folio)
    if not pedido.esta_pendiente:
        return redirect(pedido)
    if request.method == "POST":
        if request.POST.get("resultado") == "aprobar":
            servicios.confirmar_pago(pedido, f"simulado-{pedido.folio}")
            messages.success(request, "Pago de prueba aprobado.")
        else:
            messages.error(request, "Pago de prueba rechazado. Puedes intentarlo de nuevo.")
        return redirect(pedido)
    return render(request, "pedidos/pago_simulado.html", {"pedido": pedido})


@csrf_exempt  # Stripe no puede enviar el token CSRF; la seguridad la da la firma
@require_POST
def webhook_stripe(request):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise Http404
    try:
        evento = pagos.verificar_evento(request.body, request.headers.get("Stripe-Signature", ""))
    except (ValueError, stripe.SignatureVerificationError):
        return HttpResponseBadRequest("Firma no válida.")
    servicios.procesar_evento_stripe(evento)
    return HttpResponse(status=200)
