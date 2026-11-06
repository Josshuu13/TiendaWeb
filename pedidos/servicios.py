"""
Reglas de negocio de los pedidos.

Todo cambio importante pasa por estas funciones, sin importar si lo pide el cliente,
el admin o Stripe. Así las reglas viven en un solo lugar y son fáciles de probar.
Cada función es atómica: se hace completa o no se hace nada.
"""
import logging

import stripe
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from catalogo.entregas import rango_entrega
from catalogo.models import Variante

from . import notificaciones, pagos
from .models import EventoPago, EventoPedido, LineaPedido, Pedido, SolicitudPosventa

logger = logging.getLogger(__name__)
Estado = Pedido.Estado


class ErrorPedido(Exception):
    """La operación no se puede realizar; el mensaje es apto para el cliente."""


def _registrar_evento(pedido, nota=""):
    EventoPedido.objects.create(pedido=pedido, estado=pedido.estado, nota=nota)
    transaction.on_commit(lambda: notificaciones.avisar_cambio(pedido))


@transaction.atomic
def crear_pedido(usuario, resumen, datos_envio) -> Pedido:
    """Crea el pedido con los importes del servidor y aparta las existencias."""
    if not resumen.lineas:
        raise ErrorPedido("Tu carrito está vacío.")
    if resumen.tiene_errores:
        raise ErrorPedido("Revisa tu carrito: hay productos que cambiaron.")

    minima, maxima = rango_entrega(resumen.dias_elaboracion)
    pedido = Pedido.objects.create(
        usuario=usuario,
        subtotal=resumen.subtotal,
        costo_envio=resumen.envio,
        total=resumen.total,
        entrega_minima=minima,
        entrega_maxima=maxima,
        **datos_envio,
    )
    for linea in resumen.lineas:
        cot = linea.cotizacion
        if cot.variante:
            # La condición va en el UPDATE para que dos compras simultáneas no vendan
            # la misma pieza: si no alcanza, no se actualiza ninguna fila.
            apartadas = Variante.objects.filter(
                pk=cot.variante.pk, existencias__gte=cot.cantidad,
            ).update(existencias=F("existencias") - cot.cantidad)
            if not apartadas:
                raise ErrorPedido(f"Ya no hay suficientes piezas de {cot.producto.nombre}.")
        LineaPedido.objects.create(
            pedido=pedido,
            producto=cot.producto,
            variante=cot.variante,
            nombre=cot.producto.nombre,
            seleccion=cot.seleccion,
            opciones=linea.seleccion.get("opciones", {}),
            vista_previa=linea.vista,
            precio_unitario=cot.precio_unitario,
            cantidad=cot.cantidad,
        )
    EventoPedido.objects.create(pedido=pedido, estado=pedido.estado)
    return pedido


def _reponer_existencias(pedido):
    for linea in pedido.lineas.exclude(variante=None):
        Variante.objects.filter(pk=linea.variante_id).update(existencias=F("existencias") + linea.cantidad)


@transaction.atomic
def confirmar_pago(pedido, referencia="") -> bool:
    """Marca el pedido como pagado. Si ya lo estaba, no hace nada y devuelve False."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if pedido.estado != Estado.PENDIENTE_PAGO:
        logger.warning("Pago recibido para %s en estado %s", pedido.folio, pedido.estado)
        return False
    pedido.estado = Estado.CONFIRMADO
    pedido.referencia_pago = referencia
    pedido.pagado_en = timezone.now()
    pedido.save(update_fields=["estado", "referencia_pago", "pagado_en", "actualizado"])
    _registrar_evento(pedido, "Pago confirmado.")
    return True


@transaction.atomic
def cambiar_estado(pedido, nuevo, nota="") -> Pedido:
    """Avanza el pedido si la regla lo permite y repone existencias cuando corresponde."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    nuevo = Estado(nuevo)
    if nuevo not in Pedido.TRANSICIONES[Estado(pedido.estado)]:
        raise ErrorPedido(f"No se puede pasar de {pedido.get_estado_display()} a {nuevo.label}.")
    if nuevo == Estado.ENVIADO and not (pedido.transportista and pedido.numero_guia):
        raise ErrorPedido("Captura el transportista y el número de guía antes de enviar.")
    if nuevo in (Estado.CANCELADO, Estado.DEVUELTO):
        _reponer_existencias(pedido)
    pedido.estado = nuevo
    pedido.save(update_fields=["estado", "actualizado"])
    _registrar_evento(pedido, nota)
    return pedido


@transaction.atomic
def crear_solicitud(pedido, tipo, motivo) -> SolicitudPosventa:
    """Registra la solicitud del cliente; el equipo la resuelve desde el admin."""
    Tipo = SolicitudPosventa.Tipo
    if pedido.solicitud_abierta:
        raise ErrorPedido("Este pedido ya tiene una solicitud en revisión.")
    if tipo == Tipo.CANCELACION and not pedido.puede_cancelarse:
        raise ErrorPedido("Este pedido ya no se puede cancelar.")
    if tipo == Tipo.DEVOLUCION and not pedido.puede_devolverse:
        raise ErrorPedido("Solo se pueden devolver pedidos entregados.")
    return SolicitudPosventa.objects.create(pedido=pedido, tipo=tipo, motivo=motivo)


@transaction.atomic
def resolver_solicitud(solicitud, aprobar, respuesta="") -> SolicitudPosventa:
    """Aprueba o rechaza. Al aprobar: cambia el pedido, repone piezas y reembolsa."""
    Tipo, EstadoSolicitud = SolicitudPosventa.Tipo, SolicitudPosventa.Estado
    solicitud = SolicitudPosventa.objects.select_for_update().get(pk=solicitud.pk)
    if solicitud.estado != EstadoSolicitud.SOLICITADA:
        raise ErrorPedido("Esta solicitud ya fue resuelta.")

    if aprobar:
        nuevo = Estado.CANCELADO if solicitud.tipo == Tipo.CANCELACION else Estado.DEVUELTO
        # Primero el estado: si no se permite, no se toca el dinero. Si Stripe falla, el
        # error deshace también el cambio de estado.
        pedido = cambiar_estado(solicitud.pedido, nuevo, "Solicitud aprobada; reembolso registrado.")
        try:
            pagos.reembolsar(pedido)
        except stripe.StripeError as e:
            logger.exception("No se pudo reembolsar %s", pedido.folio)
            raise ErrorPedido("Stripe no pudo hacer el reembolso; intenta de nuevo.") from e

    solicitud.estado = EstadoSolicitud.APROBADA if aprobar else EstadoSolicitud.RECHAZADA
    solicitud.respuesta = respuesta
    solicitud.resuelta = timezone.now()
    solicitud.save(update_fields=["estado", "respuesta", "resuelta"])
    return solicitud


@transaction.atomic
def procesar_evento_stripe(evento: dict) -> bool:
    """Aplica un aviso de Stripe una sola vez. Devuelve False si ya se había recibido.

    Si algo falla, también se deshace el registro del aviso y Stripe lo reintenta.
    """
    _, es_nuevo = EventoPago.objects.get_or_create(
        evento_id=evento["id"], defaults={"tipo": evento["type"]},
    )
    if not es_nuevo:
        return False

    sesion = evento["data"]["object"]
    pedido = Pedido.objects.filter(folio=sesion.get("client_reference_id")).first()
    if pedido is None:
        logger.warning("Aviso de Stripe sin pedido: %s", evento["id"])
        return True

    if evento["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        if sesion.get("payment_status") != "paid":
            return True  # método diferido: Stripe avisará cuando el dinero llegue
        if sesion.get("amount_total") != pagos.centavos(pedido.total):
            logger.error("Importe distinto en %s: %s", pedido.folio, sesion.get("amount_total"))
            return True
        confirmar_pago(pedido, sesion.get("payment_intent") or sesion["id"])
    elif evento["type"] == "checkout.session.expired" and pedido.esta_pendiente:
        cambiar_estado(pedido, Estado.CANCELADO, "El tiempo para pagar terminó.")
    return True
