"""Pruebas del comando que revisa la configuración de Stripe."""
from io import StringIO

import pytest
import stripe
from django.core.management import CommandError, call_command


def correr(*args):
    salida = StringIO()
    call_command("verificar_stripe", *args, stdout=salida)
    return salida.getvalue()


@pytest.fixture
def llaves(settings):
    settings.STRIPE_SECRET_KEY = "sk_test_prueba"
    settings.STRIPE_WEBHOOK_SECRET = "whsec_prueba"
    return settings


def test_sin_llave_avisa_que_hay_pago_simulado(settings):
    settings.STRIPE_SECRET_KEY = ""
    with pytest.raises(CommandError, match="pago simulado"):
        correr()


def test_rechaza_llaves_de_modo_real(llaves):
    llaves.STRIPE_SECRET_KEY = "sk_live_peligrosa"
    with pytest.raises(CommandError, match="modo real"):
        correr("--sin-conexion")


def test_falta_el_secreto_del_webhook(llaves):
    llaves.STRIPE_WEBHOOK_SECRET = ""
    with pytest.raises(CommandError, match="STRIPE_WEBHOOK_SECRET"):
        correr("--sin-conexion")


def test_todo_correcto_con_stripe_simulado(llaves, monkeypatch):
    llamadas = []
    monkeypatch.setattr(stripe.Balance, "retrieve", lambda **datos: llamadas.append(datos))
    salida = correr()
    assert llamadas == [{"api_key": "sk_test_prueba"}]
    assert "Stripe aceptó la llave" in salida and "/pagos/webhook/" in salida


def test_llave_rechazada_por_stripe(llaves, monkeypatch):
    def falla(**datos):
        raise stripe.AuthenticationError("Invalid API Key")

    monkeypatch.setattr(stripe.Balance, "retrieve", falla)
    with pytest.raises(CommandError, match="rechazó la llave"):
        correr()
