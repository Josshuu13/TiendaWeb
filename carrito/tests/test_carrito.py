"""Pruebas del carrito: siempre usa precios y existencias actuales del servidor."""
import base64
import io
from decimal import Decimal

import pytest
from django.urls import reverse
from PIL import Image

from carrito.carrito import Carrito, vista_valida
from catalogo.models import Producto, Variante
from conftest import agregar, seleccion_calcetin, seleccion_mono, seleccion_sueter
from pedidos.models import ConfiguracionTienda

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def datos(catalogo):
    pass


def resumen(client):
    return Carrito(client.session).resumen(ConfiguracionTienda.cargar().costo_envio)


def test_agregar_suma_piezas_y_junta_repetidos(client):
    agregar(client, seleccion_sueter(cantidad=1))
    r = agregar(client, seleccion_sueter(cantidad=2))
    assert r.json() == {"ok": True, "piezas": 3}
    assert len(resumen(client).lineas) == 1


def test_carrito_mixto_con_personalizacion(client):
    agregar(client, seleccion_mono())
    agregar(client, seleccion_sueter())
    agregar(client, seleccion_calcetin())
    r = resumen(client)
    assert len(r.lineas) == 3
    assert r.subtotal == Decimal("120.00") + Decimal("480.00") + Decimal("110.00")
    assert r.total == r.subtotal + ConfiguracionTienda.cargar().costo_envio


def test_el_precio_enviado_por_el_cliente_se_ignora(client):
    agregar(client, {**seleccion_sueter(), "precio": "1.00", "total": "1.00"})
    assert resumen(client).subtotal == Decimal("480.00")


def test_si_cambia_el_precio_el_carrito_lo_refleja(client):
    agregar(client, seleccion_sueter())
    Producto.objects.filter(slug="sueter-santa").update(precio_base=Decimal("500.00"))
    assert resumen(client).subtotal == Decimal("500.00")


def test_no_se_agrega_mas_de_lo_que_hay_ni_sumando(client):
    v = Variante.objects.get(producto__slug="sueter-santa", talla="M")
    agregar(client, seleccion_sueter(cantidad=v.existencias))
    r = agregar(client, seleccion_sueter(cantidad=1))
    assert r.status_code == 400
    assert "Solo quedan" in r.json()["error"]
    assert resumen(client).piezas == v.existencias


def test_producto_agotado_despues_marca_error(client):
    agregar(client, seleccion_sueter())
    Variante.objects.filter(producto__slug="sueter-santa").update(existencias=0)
    r = resumen(client)
    assert r.tiene_errores
    assert "agotada" in r.lineas[0].error


def test_json_malo_y_cantidad_invalida(client):
    r = client.post(reverse("carrito:agregar"), "{malo", content_type="application/json")
    assert r.status_code == 400
    assert agregar(client, seleccion_sueter(cantidad="muchas")).status_code == 400
    assert agregar(client, seleccion_sueter(cantidad=0)).status_code == 400


def test_cambiar_y_quitar_sin_javascript_redirigen(client):
    agregar(client, seleccion_sueter())
    linea = client.session["carrito"][0]["id"]
    r = client.post(reverse("carrito:actualizar", args=[linea]), {"cantidad": 2})
    assert r.status_code == 302 and resumen(client).piezas == 2
    r = client.post(reverse("carrito:quitar", args=[linea]))
    assert r.status_code == 302 and resumen(client).lineas == []


def test_con_htmx_responde_solo_el_contenido(client):
    agregar(client, seleccion_sueter())
    linea = client.session["carrito"][0]["id"]
    r = client.post(reverse("carrito:actualizar", args=[linea]), {"cantidad": 3}, HTTP_HX_REQUEST="true")
    assert r.status_code == 200
    assert r["HX-Trigger"] == "carrito-cambiado"
    html = r.content.decode()
    assert 'id="carrito-contenido"' in html and "<html" not in html


def test_cantidad_no_valida_muestra_aviso_y_conserva_la_anterior(client):
    agregar(client, seleccion_sueter(cantidad=2))
    linea = client.session["carrito"][0]["id"]
    r = client.post(reverse("carrito:actualizar", args=[linea]), {"cantidad": 999}, HTTP_HX_REQUEST="true")
    assert "entre 1 y 50" in r.content.decode()
    assert resumen(client).piezas == 2


def test_contador_muestra_las_piezas(client):
    agregar(client, seleccion_sueter(cantidad=2))
    assert "<b>2</b>" in client.get(reverse("carrito:contador")).content.decode()


def test_paginas_del_carrito_vacio_y_con_productos(client):
    assert "Tu carrito está vacío" in client.get(reverse("carrito:ver")).content.decode()
    agregar(client, seleccion_sueter())
    html = client.get(reverse("carrito:ver")).content.decode()
    assert "Suéter Santa" in html and "Continuar con la compra" in html


# --- Vista previa del moño: la manda el navegador, así que no se confía en ella ---

def imagen_png():
    salida = io.BytesIO()
    Image.new("RGBA", (10, 10), (179, 18, 46, 255)).save(salida, "PNG")
    return "data:image/png;base64," + base64.b64encode(salida.getvalue()).decode()


def test_vista_previa_valida_se_conserva(client):
    agregar(client, {**seleccion_mono(), "vista": imagen_png()})
    assert resumen(client).lineas[0].vista.startswith("data:image/png")


@pytest.mark.parametrize("vista", [
    "javascript:alert(1)",
    "data:text/html;base64,PHNjcmlwdD4=",
    "data:image/png;base64,bm8tZXMtaW1hZ2Vu",  # base64 válido, pero no es una imagen
    "data:image/png;base64," + "A" * 300_000,   # demasiado grande
    123,
])
def test_vista_previa_no_valida_se_descarta(vista):
    assert vista_valida(vista) == ""
