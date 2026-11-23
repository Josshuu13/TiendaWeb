"""
Pruebas del personalizador de calcetas.

El cliente elige el color de la calceta y de sus detalles, un diseño predefinido, su
posición, su tamaño y la talla. El servidor valida todo y calcula el precio.
"""
import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from catalogo.cotizacion import ErrorCotizacion, cotizar
from catalogo.models import Color, DisenoCalceta, Variante
from conftest import comprar, seleccion_calcetin, seleccion_mono, seleccion_sueter

pytestmark = pytest.mark.django_db
SLUG = "calcetas-personalizables"
QUITAR = object()  # para quitar una opción en una prueba


@pytest.fixture(autouse=True)
def datos(catalogo):
    pass


def color(nombre):
    return Color.objects.get(nombre=nombre).pk


def calceta(cantidad=1, **cambios):
    """Selección completa de la calceta; los cambios reemplazan o quitan opciones."""
    opciones = {
        "cuerpo": color("Rojo navidad"), "detalles": color("Blanco"), "talla": "6-8",
        "diseno": "reno", "x": 50, "y": 30, "tamano": 100,
    }
    opciones.update(cambios)
    opciones = {k: v for k, v in opciones.items() if v is not QUITAR}
    return {"producto": SLUG, "opciones": opciones, "cantidad": cantidad}


# --- Precio y selección ---

def test_precio_base_mas_diseno():
    cot = cotizar(calceta(cantidad=2))
    assert cot.precio_unitario == Decimal("124.00")  # 99 + 25 del reno
    assert cot.total == Decimal("248.00")
    assert cot.dias_elaboracion == 3


def test_sin_diseno_cobra_solo_la_base_e_ignora_la_posicion():
    cot = cotizar(calceta(diseno="", x=999))
    assert cot.precio_unitario == Decimal("99.00")
    assert cot.seleccion["Diseño"] == "Sin diseño" and "Posición" not in cot.seleccion


def test_la_seleccion_queda_legible_para_el_pedido():
    seleccion = cotizar(calceta(x=20, y=80, tamano=120)).seleccion
    assert seleccion == {
        "Color de la calceta": "Rojo navidad",
        "Puño, talón y punta": "Blanco",
        "Talla": "Niña 6-8",
        "Diseño": "Reno",
        "Posición": "20 % horizontal, 80 % vertical",
        "Tamaño": "120 %",
    }


def test_todos_los_disenos_de_ejemplo_se_pueden_cotizar():
    for diseno in DisenoCalceta.objects.filter(activo=True):
        assert cotizar(calceta(diseno=diseno.clave)).precio_unitario == Decimal("99.00") + diseno.precio_extra


# --- Lo que el servidor rechaza ---

def color_no_permitido():
    return Color.objects.exclude(partes__producto__slug=SLUG, partes__clave="cuerpo").first().pk


@pytest.mark.parametrize("cambios, mensaje", [
    ({"detalles": QUITAR}, "Elige un color"),
    ({"talla": QUITAR}, "Elige una talla"),
    ({"talla": "XL"}, "Elige una talla"),
    ({"diseno": "dragon"}, "no está disponible"),
    ({"x": 101}, "entre 0 y 100"),
    ({"y": -1}, "entre 0 y 100"),
    ({"tamano": 40}, "entre 50 y 150"),
    ({"tamano": 160}, "entre 50 y 150"),
    ({"x": "mucho"}, "no es válido"),
    ({"x": True}, "no es válido"),
    ({"precio": 1}, "no reconocidas"),
])
def test_selecciones_invalidas_se_rechazan(cambios, mensaje):
    with pytest.raises(ErrorCotizacion, match=mensaje):
        cotizar(calceta(**cambios))


def test_color_que_no_es_de_la_paleta_se_rechaza():
    with pytest.raises(ErrorCotizacion, match="no está disponible"):
        cotizar(calceta(cuerpo=color_no_permitido()))


def test_diseno_desactivado_por_falta_de_material_se_rechaza():
    DisenoCalceta.objects.filter(clave="reno").update(activo=False)
    with pytest.raises(ErrorCotizacion, match="no está disponible"):
        cotizar(calceta())


def test_api_cotiza_e_ignora_el_precio_del_cliente(client):
    datos = {**calceta(), "total": "1.00"}
    r = client.post(reverse("catalogo:api_cotizar"), json.dumps(datos), content_type="application/json")
    assert r.status_code == 200 and r.json()["total"] == "124.00"


# --- Páginas ---

def test_pagina_de_la_calceta_trae_su_personalizador(client):
    html = client.get(reverse("catalogo:producto", args=[SLUG])).content.decode()
    for texto in ('id="calceta"', "config-calceta", "js/calceta.js", "Posición y tamaño", "Reno", 'name="talla"'):
        assert texto in html
    assert 'id="simulador"' not in html  # el simulador del moño no se carga aquí


def test_el_mono_conserva_su_simulador(client):
    html = client.get(reverse("catalogo:producto", args=["mono-clasico"])).content.decode()
    assert 'id="simulador"' in html and 'id="calceta"' not in html


def test_pagina_de_calcetines_sigue_mostrando_todos(client):
    r = client.get(reverse("catalogo:categoria", args=["calcetines"]))
    nombres = [p.nombre for p in r.context["productos"]]
    assert "Calcetas personalizables" in nombres and "Calcetines Santa Claus" in nombres


def test_pagina_de_monos_sigue_destacando_el_mono(client):
    r = client.get(reverse("catalogo:categoria", args=["monos"]))
    assert r.context["personalizable"].slug == "mono-clasico"


# --- Compra ---

def test_compra_con_las_tres_lineas_y_calceta_personalizada(cliente):
    pedido = comprar(cliente, seleccion_mono(), seleccion_sueter(), seleccion_calcetin(), calceta())
    linea = pedido.lineas.get(producto__slug=SLUG)
    assert linea.seleccion["Diseño"] == "Reno" and linea.opciones["tamano"] == 100
    assert linea.precio_unitario == Decimal("124.00")
    assert linea.variante is None  # se hace sobre pedido: no aparta existencias
    assert pedido.lineas.count() == 4


def test_calceta_personalizada_no_toca_inventario(cliente):
    antes = sum(Variante.objects.values_list("existencias", flat=True))
    comprar(cliente, calceta(cantidad=3))
    assert sum(Variante.objects.values_list("existencias", flat=True)) == antes


# --- Administración ---

def test_admin_de_disenos_y_de_la_calceta(client):
    client.force_login(get_user_model().objects.create_superuser("admin", "a@example.com", "clave-de-prueba-123"))
    assert client.get(reverse("admin:catalogo_disenocalceta_changelist")).status_code == 200
    from catalogo.models import Producto
    calceta_pk = Producto.objects.get(slug=SLUG).pk
    html = client.get(reverse("admin:catalogo_producto_change", args=[calceta_pk])).content.decode()
    assert "Puño, talón y punta" in html
