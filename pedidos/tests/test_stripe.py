"""Pruebas del pago con Stripe sin conectarse a internet: se simulan sus respuestas."""
import hashlib
import hmac
import json
import time
from types import SimpleNamespace

import pytest
import stripe
from django.urls import reverse

from conftest import comprar, seleccion_sueter
from pedidos import pagos, servicios
from pedidos.models import EventoPago, Pedido

pytestmark = pytest.mark.django_db
SECRETO = "whsec_prueba"
Estado = Pedido.Estado


@pytest.fixture(autouse=True)
def datos(catalogo, settings):
    settings.STRIPE_WEBHOOK_SECRET = SECRETO


@pytest.fixture
def pedido(cliente):
    return comprar(cliente, seleccion_sueter())


def evento(pedido, tipo="checkout.session.completed", evento_id="evt_1", **sesion):
    objeto = {
        "id": "cs_test_1", "client_reference_id": pedido.folio, "payment_status": "paid",
        "amount_total": pagos.centavos(pedido.total), "payment_intent": "pi_test_1", **sesion,
    }
    return {"id": evento_id, "object": "event", "type": tipo, "data": {"object": objeto}}


def enviar(client, cuerpo, secreto=SECRETO):
    contenido = json.dumps(cuerpo)
    marca = int(time.time())
    firma = hmac.new(secreto.encode(), f"{marca}.{contenido}".encode(), hashlib.sha256).hexdigest()
    return client.post(reverse("pedidos:webhook"), contenido, content_type="application/json",
                       HTTP_STRIPE_SIGNATURE=f"t={marca},v1={firma}")


def test_aviso_firmado_confirma_el_pago(client, pedido):
    assert enviar(client, evento(pedido)).status_code == 200
    pedido.refresh_from_db()
    assert pedido.estado == Estado.CONFIRMADO and pedido.referencia_pago == "pi_test_1"


def test_aviso_con_firma_falsa_se_rechaza(client, pedido):
    assert enviar(client, evento(pedido), secreto="otro").status_code == 400
    pedido.refresh_from_db()
    assert pedido.estado == Estado.PENDIENTE_PAGO


def test_aviso_sin_firma_se_rechaza(client, pedido):
    r = client.post(reverse("pedidos:webhook"), json.dumps(evento(pedido)), content_type="application/json")
    assert r.status_code == 400


def test_regresar_de_stripe_no_confirma_el_pago(cliente, pedido):
    """Solo cuenta el aviso firmado: la pantalla del cliente no es prueba de pago."""
    cliente.get(pedido.get_absolute_url() + "?pago=ok")
    pedido.refresh_from_db()
    assert pedido.estado == Estado.PENDIENTE_PAGO


def test_aviso_repetido_se_aplica_una_sola_vez(client, pedido):
    enviar(client, evento(pedido))
    assert enviar(client, evento(pedido)).status_code == 200
    assert EventoPago.objects.count() == 1
    assert pedido.eventos.filter(estado=Estado.CONFIRMADO).count() == 1


def test_importe_distinto_no_confirma(client, pedido):
    enviar(client, evento(pedido, amount_total=100))
    pedido.refresh_from_db()
    assert pedido.estado == Estado.PENDIENTE_PAGO


def test_pago_diferido_espera_a_que_llegue_el_dinero(client, pedido):
    enviar(client, evento(pedido, payment_status="unpaid"))
    pedido.refresh_from_db()
    assert pedido.estado == Estado.PENDIENTE_PAGO
    enviar(client, evento(pedido, tipo="checkout.session.async_payment_succeeded", evento_id="evt_2"))
    pedido.refresh_from_db()
    assert pedido.estado == Estado.CONFIRMADO


def test_sesion_expirada_cancela_y_libera_piezas(client, pedido):
    from catalogo.models import Variante
    linea = pedido.lineas.get()
    antes = Variante.objects.get(pk=linea.variante_id).existencias
    enviar(client, evento(pedido, tipo="checkout.session.expired", evento_id="evt_3"))
    pedido.refresh_from_db()
    assert pedido.estado == Estado.CANCELADO
    assert Variante.objects.get(pk=linea.variante_id).existencias == antes + linea.cantidad


def test_aviso_de_un_pedido_desconocido_no_falla(client, pedido):
    cuerpo = evento(pedido, client_reference_id="PR-NOEXISTE")
    assert enviar(client, cuerpo).status_code == 200


def test_webhook_no_disponible_sin_secreto(client, settings, pedido):
    settings.STRIPE_WEBHOOK_SECRET = ""
    assert client.post(reverse("pedidos:webhook"), "{}", content_type="application/json").status_code == 404


def test_sesion_de_pago_usa_los_importes_del_servidor(cliente, settings, monkeypatch):
    settings.STRIPE_SECRET_KEY = "sk_test_prueba"
    recibido = {}

    def crear(**datos):
        recibido.update(datos)
        return SimpleNamespace(id="cs_test_9", url="https://checkout.stripe.com/c/pay/cs_test_9")

    monkeypatch.setattr(stripe.checkout.Session, "create", crear)
    cliente.post(reverse("carrito:agregar"), json.dumps(seleccion_sueter(cantidad=2)), content_type="application/json")
    from conftest import DIRECCION
    r = cliente.post(reverse("pedidos:compra"), DIRECCION)

    pedido = Pedido.objects.get()
    assert r.url == "https://checkout.stripe.com/c/pay/cs_test_9"
    assert pedido.sesion_pago == "cs_test_9"
    assert recibido["client_reference_id"] == pedido.folio
    productos, envio = recibido["line_items"]
    assert productos["quantity"] == 2 and productos["price_data"]["unit_amount"] == 48000
    assert envio["price_data"]["unit_amount"] == pagos.centavos(pedido.costo_envio)
    assert all(p["price_data"]["currency"] == "mxn" for p in recibido["line_items"])


def test_si_stripe_no_responde_el_pedido_queda_para_reintentar(cliente, settings, monkeypatch):
    settings.STRIPE_SECRET_KEY = "sk_test_prueba"

    def falla(**datos):
        raise stripe.APIConnectionError("Sin conexión")

    monkeypatch.setattr(stripe.checkout.Session, "create", falla)
    cliente.post(reverse("carrito:agregar"), json.dumps(seleccion_sueter()), content_type="application/json")
    from conftest import DIRECCION
    r = cliente.post(reverse("pedidos:compra"), DIRECCION)
    pedido = Pedido.objects.get()
    assert r.url == pedido.get_absolute_url() and pedido.esta_pendiente


def test_si_falla_el_reembolso_no_se_cancela(cliente, settings, monkeypatch):
    settings.STRIPE_SECRET_KEY = "sk_test_prueba"
    pedido = comprar_con_simulador(cliente, settings)
    servicios.confirmar_pago(pedido, "pi_test_1")
    pedido.refresh_from_db()
    solicitud = servicios.crear_solicitud(pedido, "cancelacion", "Motivo")

    def falla(**datos):
        raise stripe.APIConnectionError("Sin conexión")

    monkeypatch.setattr(stripe.Refund, "create", falla)
    with pytest.raises(servicios.ErrorPedido, match="reembolso"):
        servicios.resolver_solicitud(solicitud, True)
    pedido.refresh_from_db()
    assert pedido.estado == Estado.CONFIRMADO


def comprar_con_simulador(cliente, settings):
    llave, settings.STRIPE_SECRET_KEY = settings.STRIPE_SECRET_KEY, ""
    pedido = comprar(cliente, seleccion_sueter())
    settings.STRIPE_SECRET_KEY = llave
    return pedido
