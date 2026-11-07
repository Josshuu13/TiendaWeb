"""Pruebas de seguridad, buscadores y accesibilidad básica."""
import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def datos(catalogo):
    pass


def test_encabezados_de_seguridad(client):
    r = client.get(reverse("catalogo:inicio"))
    politica = r["Content-Security-Policy"]
    assert "default-src 'self'" in politica and "frame-ancestors 'none'" in politica
    assert "'unsafe-eval'" not in politica and "script-src 'self';" in politica
    assert r["X-Frame-Options"] == "DENY"
    assert r["X-Content-Type-Options"] == "nosniff"
    assert "Permissions-Policy" in r


def test_ya_no_se_carga_nada_de_otros_dominios(client):
    html = client.get(reverse("catalogo:inicio")).content.decode()
    assert "cdn.jsdelivr.net" not in html and "fonts.googleapis.com" not in html
    assert "<script>" not in html  # sin scripts en línea: los bloquearía la política


def test_ficha_de_producto_para_buscadores(client):
    html = client.get(reverse("catalogo:producto", args=["sueter-santa"])).content.decode()
    assert '<script type="application/ld+json">' in html
    assert '"priceCurrency": "MXN"' in html and '"price": "480.00"' in html


def test_robots_y_mapa_del_sitio(client):
    robots = client.get("/robots.txt").content.decode()
    assert "Disallow: /pedidos/" in robots and "sitemap.xml" in robots
    mapa = client.get("/sitemap.xml").content.decode()
    assert "/producto/sueter-santa/" in mapa and "/producto/sueter-reno/" not in mapa


def test_revision_de_salud(client):
    assert client.get("/salud/").json() == {"ok": True}


def test_pagina_404_propia(client):
    r = client.get("/no-existe/")
    assert r.status_code == 404 and "No encontramos esta página" in r.content.decode()


@pytest.mark.parametrize("nombre", ["catalogo:privacidad", "catalogo:terminos"])
def test_paginas_legales(client, nombre):
    assert client.get(reverse(nombre)).status_code == 200


def test_suéteres_de_la_coleccion_tienen_imagen(client):
    r = client.get(reverse("catalogo:categoria", args=["sueteres"]))
    productos = list(r.context["productos"])
    assert len(productos) == 5
    assert all(p.url_imagen_estatica for p in productos)
    assert all(not p.personalizable for p in productos)
    assert "img/sueteres/sueter-santa.webp" in r.content.decode()


def test_suéter_sin_simulador_y_con_talla(client):
    html = client.get(reverse("catalogo:producto", args=["sueter-santa"])).content.decode()
    assert 'id="simulador"' not in html and 'id="tallas"' in html and "Agregar al carrito" in html


def test_suéter_retirado_no_aparece(client):
    assert client.get(reverse("catalogo:producto", args=["sueter-reno"])).status_code == 404


def test_pagina_sin_bootstrap(client):
    html = client.get(reverse("catalogo:producto", args=["mono-clasico"])).content.decode()
    assert "bootstrap" not in html.lower()
    assert 'class="col-' not in html and 'data-bs-' not in html
