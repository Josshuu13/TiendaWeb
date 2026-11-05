"""Pruebas de la portada, las listas con filtros, la ayuda y la fecha de entrega."""
import datetime

import pytest
from django.core.management import call_command
from django.urls import reverse

from catalogo.entregas import rango_entrega, sumar_dias_habiles, texto_entrega
from catalogo.models import Color, Producto

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalogo_demo():
    call_command("cargar_datos_demo", verbosity=0)


# --- Fecha de entrega (solo días hábiles) ---

def test_sumar_dias_habiles_salta_fin_de_semana():
    viernes = datetime.date(2026, 11, 6)
    assert sumar_dias_habiles(viernes, 1) == datetime.date(2026, 11, 9)  # lunes


def test_rango_entrega_suma_elaboracion_y_envio(settings):
    settings.DIAS_ENVIO = 3
    miercoles = datetime.date(2026, 11, 4)
    minima, maxima = rango_entrega(3, hoy=miercoles)   # 3 + 3 = 6 días hábiles
    assert minima == datetime.date(2026, 11, 12)       # jueves
    assert maxima == datetime.date(2026, 11, 16)       # +2 hábiles: lunes


def test_texto_entrega_es_legible(settings):
    settings.DIAS_ENVIO = 3
    texto = texto_entrega(0, hoy=datetime.date(2026, 11, 4))
    assert texto == "Si pides hoy, llega entre el lunes 9 y el miércoles 11 de noviembre."


# --- Kits ---

def test_kits_tienen_descuento():
    kits = Producto.objects.filter(categoria__slug="kits")
    assert kits.count() == 4
    assert all(k.ahorro > 0 for k in kits)


# --- Páginas ---

def test_portada_muestra_categorias_y_kits(client):
    html = client.get(reverse("catalogo:inicio")).content.decode()
    assert "Compra por categoría" in html
    assert "Kits navideños a juego" in html
    assert "Suéteres navideños" in html


def test_filtro_por_color(client):
    verde = Color.objects.get(nombre="Verde pino")
    r = client.get(reverse("catalogo:categoria", args=["sueteres"]), {"color": verde.pk})
    nombres = [p.nombre for p in r.context["productos"]]
    assert "Suéter Copos" in nombres and "Suéter Reno" in nombres  # el Reno también viene en verde


def test_filtro_por_talla_adulto(client):
    r = client.get(reverse("catalogo:categoria", args=["calcetines"]), {"talla": "adulto"})
    assert list(r.context["productos"]) == []  # los calcetines no tienen tallas de adulto


def test_pagina_de_sueter_trae_variantes_y_entrega(client):
    r = client.get(reverse("catalogo:producto", args=["sueter-reno"]))
    config = r.context["config_variantes"]
    assert len(config["colores"]) == 2
    assert any(v["existencias"] == 0 for v in config["variantes"])  # hay una talla agotada
    assert "Si pides hoy" in r.content.decode()


def test_ayuda_muestra_politicas(client):
    html = client.get(reverse("catalogo:ayuda")).content.decode()
    for texto in ("Envíos y entregas", "Cambios y devoluciones", "Cancelar un pedido"):
        assert texto in html
