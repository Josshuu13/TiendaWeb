"""Pruebas de la cotización validada en el servidor."""
import json
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.urls import reverse

from catalogo.cotizacion import ErrorCotizacion, cotizar
from catalogo.models import Color, Producto, Variante

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalogo_demo():
    call_command("cargar_datos_demo", verbosity=0)


def color(nombre):
    return Color.objects.get(nombre=nombre).pk


def mono(opciones, cantidad=1):
    return {"producto": "mono-clasico", "opciones": opciones, "cantidad": cantidad}


# --- Moño personalizable ---

def test_mono_sin_decoracion_cuesta_el_precio_base():
    cot = cotizar(mono({"lazos": color("Rojo navidad"), "nudo": color("Blanco nieve")}))
    assert cot.precio_unitario == Decimal("120.00")
    assert cot.seleccion["Lazos"] == "Rojo navidad"


def test_decoracion_suma_precio_y_dias():
    cot = cotizar(mono({"lazos": color("Lila"), "nudo": color("Dorado"), "decoracion": "copo"}, 3))
    assert cot.precio_unitario == Decimal("138.00")  # 120 + 18
    assert cot.total == Decimal("414.00")
    assert cot.dias_elaboracion == 4  # 3 del moño + 1 del copo


def test_falta_color_de_una_parte():
    with pytest.raises(ErrorCotizacion, match="nudo"):
        cotizar(mono({"lazos": color("Rojo navidad")}))


def test_color_inactivo_se_rechaza():
    Color.objects.filter(nombre="Negro").update(activo=False)
    with pytest.raises(ErrorCotizacion):
        cotizar(mono({"lazos": color("Negro"), "nudo": color("Dorado")}))


def test_opcion_inventada_se_rechaza():
    with pytest.raises(ErrorCotizacion, match="no reconocidas"):
        cotizar(mono({"lazos": color("Lila"), "nudo": color("Lila"), "precio": 1}))


@pytest.mark.parametrize("cantidad", [0, -2, 51, "muchos"])
def test_cantidad_fuera_de_rango(cantidad):
    with pytest.raises(ErrorCotizacion):
        cotizar(mono({"lazos": color("Lila"), "nudo": color("Lila")}, cantidad))


# --- Productos de catálogo ---

def test_sueter_talla_grande_tiene_extra():
    v = Variante.objects.get(producto__slug="sueter-reno", talla="G")
    cot = cotizar({"producto": "sueter-reno", "variante": v.sku, "cantidad": 2})
    assert cot.precio_unitario == Decimal("490.00")
    assert cot.total == Decimal("980.00")


def test_variante_agotada():
    v = Variante.objects.get(producto__slug="mono-escolar", existencias=0)
    with pytest.raises(ErrorCotizacion, match="agotada"):
        cotizar({"producto": "mono-escolar", "variante": v.sku})


def test_no_se_puede_pedir_mas_de_lo_que_hay():
    v = Variante.objects.filter(producto__slug="calcetines-santa").first()
    with pytest.raises(ErrorCotizacion, match="Solo quedan"):
        cotizar({"producto": "calcetines-santa", "variante": v.sku, "cantidad": v.existencias + 1})


def test_variante_de_otro_producto_se_rechaza():
    ajena = Variante.objects.filter(producto__slug="sueter-copos").first()
    with pytest.raises(ErrorCotizacion):
        cotizar({"producto": "sueter-reno", "variante": ajena.sku})


def test_producto_inactivo_no_se_cotiza():
    Producto.objects.filter(slug="sueter-reno").update(activo=False)
    with pytest.raises(ErrorCotizacion):
        cotizar({"producto": "sueter-reno", "variante": "X"})


# --- API y páginas ---

def test_api_devuelve_desglose(client):
    datos = mono({"lazos": color("Rosa pastel"), "nudo": color("Blanco nieve"), "decoracion": "perla"})
    r = client.post(reverse("catalogo:api_cotizar"), json.dumps(datos), content_type="application/json")
    assert r.status_code == 200
    assert r.json()["total"] == "135.00"


def test_api_ignora_precio_enviado_por_el_cliente(client):
    datos = mono({"lazos": color("Lila"), "nudo": color("Lila")})
    datos["total"] = "1.00"
    r = client.post(reverse("catalogo:api_cotizar"), json.dumps(datos), content_type="application/json")
    assert r.json()["total"] == "120.00"


def test_api_error_es_400(client):
    r = client.post(reverse("catalogo:api_cotizar"), "{malo", content_type="application/json")
    assert r.status_code == 400


@pytest.mark.parametrize("nombre, args", [
    ("catalogo:inicio", []),
    ("catalogo:lista", []),
    ("catalogo:categoria", ["sueteres"]),
    ("catalogo:producto", ["mono-clasico"]),
    ("catalogo:producto", ["calcetines-rayas"]),
])
def test_paginas_cargan(client, nombre, args):
    assert client.get(reverse(nombre, args=args)).status_code == 200
