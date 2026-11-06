"""
Conexión con Stripe (modo de pruebas).

Se usa Stripe Checkout: el cliente escribe los datos de su tarjeta en la página de
Stripe, así que nunca pasan por este servidor. El pago se da por bueno solo cuando
Stripe lo confirma por webhook con un aviso firmado, no cuando el cliente regresa.
"""
import json
import time

import stripe
from django.conf import settings

MINUTOS_PARA_PAGAR = 30


def stripe_activo():
    return bool(settings.STRIPE_SECRET_KEY)


def centavos(importe) -> int:
    """Stripe recibe los importes en centavos."""
    return int(importe * 100)


def crear_sesion_checkout(pedido, url_exito, url_cancelar) -> str:
    """Crea la página de pago de Stripe con los importes del servidor y devuelve su URL."""
    productos = [
        {
            "quantity": linea.cantidad,
            "price_data": {
                "currency": "mxn",
                "unit_amount": centavos(linea.precio_unitario),
                "product_data": {"name": linea.nombre},
            },
        }
        for linea in pedido.lineas.all()
    ]
    if pedido.costo_envio:
        productos.append({
            "quantity": 1,
            "price_data": {
                "currency": "mxn",
                "unit_amount": centavos(pedido.costo_envio),
                "product_data": {"name": "Envío"},
            },
        })
    sesion = stripe.checkout.Session.create(
        api_key=settings.STRIPE_SECRET_KEY,
        mode="payment",
        line_items=productos,
        client_reference_id=pedido.folio,
        customer_email=pedido.usuario.email,
        success_url=url_exito,
        cancel_url=url_cancelar,
        expires_at=int(time.time()) + MINUTOS_PARA_PAGAR * 60,
    )
    pedido.sesion_pago = sesion.id
    pedido.save(update_fields=["sesion_pago", "actualizado"])
    return sesion.url


def verificar_evento(contenido: bytes, firma: str) -> dict:
    """Comprueba que el aviso venga de Stripe. Lanza un error si la firma no coincide."""
    stripe.Webhook.construct_event(contenido, firma, settings.STRIPE_WEBHOOK_SECRET)
    return json.loads(contenido)


def reembolsar(pedido) -> None:
    """Devuelve el dinero en Stripe. En el pago simulado no hay nada que devolver."""
    if stripe_activo() and pedido.referencia_pago.startswith("pi_"):
        stripe.Refund.create(
            api_key=settings.STRIPE_SECRET_KEY,
            payment_intent=pedido.referencia_pago,
            idempotency_key=f"reembolso-{pedido.folio}",  # evita reembolsar dos veces
        )
