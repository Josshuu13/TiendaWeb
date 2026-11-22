"""Pruebas de la portada, las listas con filtros, la ayuda y la fecha de entrega."""
import datetime
from decimal import Decimal

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

def test_kits_tienen_descuento_real():
    # El precio tachado es la suma de las piezas, así que el ahorro es real.
    kits = Producto.objects.filter(categoria__slug="kits", activo=True)
    assert kits.count() == 5
    for k in kits:
        assert k.precio_anterior == k.precio_por_separado and k.ahorro > 0


def test_kit_con_sueter_se_vende_en_las_tallas_del_sueter():
    kit, sueter = Producto.objects.get(slug="kit-santa"), Producto.objects.get(slug="sueter-santa")
    tallas = lambda p: sorted((v.talla, v.precio_extra) for v in p.variantes.filter(activa=True))  # noqa: E731
    assert tallas(kit) == tallas(sueter)                 # mismas tallas y mismo extra en Grande
    assert [p.producto.slug for p in kit.piezas.all()] == [
        "sueter-santa", "calcetines-santa-claus", "mono-munecos-nieve-rojo"]


def test_kit_mini_es_unitalla():
    assert list(Producto.objects.get(slug="kit-mini").variantes.values_list("talla", flat=True)) == ["UNI"]


def test_pagina_del_kit_muestra_lo_que_incluye(client):
    html = client.get(reverse("catalogo:producto", args=["kit-santa"])).content.decode()
    assert "Incluye" in html and "Por separado" in html
    for nombre in ["Suéter Santa", "Calcetines Santa Claus", "Moño muñecos de nieve rojo"]:
        assert nombre in html
    assert "Talla del suéter" in html and "data-ocultar" in html   # sin selector de color


def test_lista_de_kits_sin_filtro_de_color_y_con_resumen(client):
    html = client.get(reverse("catalogo:categoria", args=["kits"])).content.decode()
    assert "?color=" not in html
    assert "Suéter + calcetines + moño" in html and "Calcetines + moño" in html
    assert html.index("Kit Santa") < html.index("Kit Mini")   # los completos primero


def test_kits_anteriores_se_retiran():
    from catalogo.management.commands.cargar_datos_demo import KITS_RETIRADOS
    assert not Producto.objects.filter(slug__in=KITS_RETIRADOS, activo=True).exists()


def test_generar_imagenes_kits(tmp_path):
    from catalogo.management.commands.cargar_datos_demo import KITS
    call_command("generar_imagenes_kits", destino=str(tmp_path))
    assert sorted(f.name for f in tmp_path.iterdir()) == sorted(f"{k[0]}.webp" for k in KITS)


def test_cotizar_kit_con_talla_grande_suma_el_extra():
    from catalogo.cotizacion import cotizar
    v = Producto.objects.get(slug="kit-santa").variantes.get(talla="G")
    assert cotizar({"producto": "kit-santa", "variante": v.sku}).total == Decimal("639.00")   # 599 + 40


# --- Páginas ---

def test_portada_muestra_categorias_y_kits(client):
    html = client.get(reverse("catalogo:inicio")).content.decode()
    assert "Compra por categoría" in html
    assert "Kits navideños" in html
    assert "Suéteres navideños" in html


def test_filtro_por_color(client):
    verde = Color.objects.get(nombre="Verde pino")
    r = client.get(reverse("catalogo:categoria", args=["sueteres"]), {"color": verde.pk})
    nombres = [p.nombre for p in r.context["productos"]]
    assert nombres == ["Suéter Osito"]


def test_filtro_por_talla_adulto(client):
    r = client.get(reverse("catalogo:categoria", args=["calcetines"]), {"talla": "adulto"})
    assert list(r.context["productos"]) == []  # los calcetines no tienen tallas de adulto


def test_pagina_de_sueter_trae_variantes_y_entrega(client):
    r = client.get(reverse("catalogo:producto", args=["sueter-osito"]))
    config = r.context["config_variantes"]
    assert len(config["colores"]) == 1
    assert any(v["existencias"] == 0 for v in config["variantes"])  # hay una talla agotada
    assert "Si pides hoy" in r.content.decode()


def test_ayuda_muestra_politicas(client):
    html = client.get(reverse("catalogo:ayuda")).content.decode()
    for texto in ("Envíos y entregas", "Cambios y devoluciones", "Cancelar un pedido"):
        assert texto in html
