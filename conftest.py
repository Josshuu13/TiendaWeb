"""Datos y ayudas que comparten las pruebas de carrito, cuentas y pedidos."""
import json

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from catalogo.models import Color, Variante

PARTES = ["patas", "baseabajo", "basearriba", "decorado", "tiras", "nudo"]
DIRECCION = {
    "nombre_destinatario": "Ana Prueba",
    "telefono": "5512345678",
    "calle": "Av. Universidad 3000",
    "colonia": "Copilco",
    "codigo_postal": "04510",
    "ciudad": "Coyoacán",
    "entidad": "Ciudad de México",
    "referencias": "",
}


@pytest.fixture
def catalogo(db):
    call_command("cargar_datos_demo", verbosity=0)


@pytest.fixture
def usuario(db):
    return get_user_model().objects.create_user(
        "ana@example.com", "ana@example.com", "clave-de-prueba-123", first_name="Ana",
    )


@pytest.fixture
def otro_usuario(db):
    return get_user_model().objects.create_user("beto@example.com", "beto@example.com", "clave-de-prueba-123")


@pytest.fixture
def cliente(client, usuario):
    """Navegador con la sesión de Ana iniciada."""
    client.force_login(usuario)
    return client


def seleccion_sueter(slug="sueter-santa", talla="M", cantidad=1):
    return {"producto": slug, "variante": Variante.objects.get(producto__slug=slug, talla=talla).sku,
            "cantidad": cantidad}


def seleccion_calcetin(cantidad=1):
    return {"producto": "calcetines-santa",
            "variante": Variante.objects.filter(producto__slug="calcetines-santa").first().sku,
            "cantidad": cantidad}


def seleccion_mono(cantidad=1):
    rojo = Color.objects.get(nombre="Rojo navidad").pk
    return {"producto": "mono-clasico", "opciones": dict.fromkeys(PARTES, rojo), "cantidad": cantidad}


def agregar(client, seleccion):
    return client.post(reverse("carrito:agregar"), json.dumps(seleccion), content_type="application/json")


def comprar(client, *selecciones):
    """Hace el recorrido completo hasta crear el pedido y lo devuelve."""
    for seleccion in selecciones:
        assert agregar(client, seleccion).status_code == 200
    respuesta = client.post(reverse("pedidos:compra"), DIRECCION)
    assert respuesta.status_code == 302
    from pedidos.models import Pedido
    return Pedido.objects.order_by("-id").first()
