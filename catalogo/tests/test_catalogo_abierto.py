"""
Pruebas de que la tienda sirve para cualquier producto y temporada.

Estas pruebas NO cargan el catálogo de ejemplo: empiezan con la base vacía, igual que una
tienda real que da de alta sus propios productos.
"""
import datetime
import io
import json
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from catalogo.models import Categoria, Producto, Temporada, Variante

pytestmark = pytest.mark.django_db


@pytest.fixture
def taza():
    categoria = Categoria.objects.create(nombre="Hogar", slug="hogar")
    producto = Producto.objects.create(categoria=categoria, nombre="Taza de barro", slug="taza-de-barro",
                                       precio_base=Decimal("150.00"), destacado=True)
    Variante.objects.create(producto=producto, existencias=5)
    return producto


def temporada(**campos):
    datos = {"nombre": "Regreso a clases", "slug": "regreso-a-clases", "titulo": "Ya casi empiezan las clases",
             "aviso": "El pretexto: regreso a clases.", "activa": True}
    return Temporada.objects.create(**{**datos, **campos})


def test_tienda_vacia_funciona(client):
    assert client.get(reverse("catalogo:inicio")).status_code == 200
    assert client.get(reverse("catalogo:lista")).status_code == 200


def test_el_nombre_viene_de_la_configuracion(client, settings):
    settings.NOMBRE_TIENDA = "Otra Marca"
    html = client.get(reverse("catalogo:inicio")).content.decode()
    assert "Otra Marca" in html and "Pretexto" not in html


def test_portada_sin_temporada_no_menciona_navidad(client, taza):
    html = client.get(reverse("catalogo:inicio")).content.decode()
    assert "Taza de barro" in html
    assert "Navidad" not in html and "navide" not in html and 'class="aviso"' not in html


def test_categoria_nueva_aparece_en_el_menu_y_en_la_portada(client, taza):
    html = client.get(reverse("catalogo:inicio")).content.decode()
    assert 'href="/catalogo/hogar/"' in html


def test_producto_nuevo_sin_foto_usa_dibujo_generico(client, taza):
    html = client.get(taza.get_absolute_url()).content.decode()
    assert 'aria-label="Foto pendiente"' in html and "kit-piezas" not in html


def test_producto_nuevo_se_puede_comprar(client, taza):
    usuario = get_user_model().objects.create_user("c@example.com", "c@example.com", "clave-de-prueba-123")
    client.force_login(usuario)
    sku = taza.variantes.get().sku
    r = client.post(reverse("carrito:agregar"),
                    json.dumps({"producto": taza.slug, "variante": sku, "cantidad": 2}),
                    content_type="application/json")
    assert r.status_code == 200
    from conftest import DIRECCION
    client.post(reverse("pedidos:compra"), DIRECCION)
    pedido = usuario.pedidos.get()
    assert pedido.subtotal == Decimal("300.00")
    assert taza.variantes.get().existencias == 3


def test_sku_se_genera_y_no_se_repite(taza):
    otra = Producto.objects.create(categoria=taza.categoria, nombre="Taza", slug="taza-de-barro-2",
                                   precio_base=Decimal("1"))
    primera = taza.variantes.get()
    primera.sku = "TAZA-DE-BARRO-2-UNI-STD"
    primera.save()
    segunda = Variante.objects.create(producto=otra)
    assert segunda.sku.startswith("TAZA-DE-BARRO-2-UNI-STD-")


def test_alta_completa_desde_el_admin_con_foto(client, settings, tmp_path):
    """El recorrido que hará el equipo: producto, foto y dos variantes sin escribir SKU."""
    settings.MEDIA_ROOT = tmp_path
    categoria = Categoria.objects.create(nombre="Hogar", slug="hogar")
    client.force_login(get_user_model().objects.create_superuser("admin", "a@example.com", "clave-de-prueba-123"))
    salida = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(salida, "PNG")
    r = client.post(reverse("admin:catalogo_producto_add"), {
        "categoria": categoria.pk, "nombre": "Vela", "slug": "vela", "descripcion": "Aroma a canela.",
        "precio_base": "99.00", "dias_elaboracion": 0, "activo": "on",
        "imagen": SimpleUploadedFile("vela.png", salida.getvalue(), content_type="image/png"),
        "variantes-TOTAL_FORMS": 2, "variantes-INITIAL_FORMS": 0,
        "variantes-0-talla": "CH", "variantes-0-existencias": 3, "variantes-0-precio_extra": 0,
        "variantes-0-activa": "on",
        "variantes-1-talla": "G", "variantes-1-existencias": 4, "variantes-1-precio_extra": 20,
        "variantes-1-activa": "on",
    })
    assert r.status_code == 302
    vela = Producto.objects.get(slug="vela")
    assert vela.variantes.count() == 2 and all(v.sku for v in vela.variantes.all())
    assert "productos/vela" in client.get(vela.get_absolute_url()).content.decode()


# --- Temporadas ---

def test_temporada_activa_cambia_portada_y_aviso(client, taza):
    t = temporada(producto_principal=taza, boton_texto="Ver la taza")
    t.productos.add(taza)
    html = client.get(reverse("catalogo:inicio")).content.decode()
    for texto in ("Ya casi empiezan las clases", "El pretexto: regreso a clases.", "Ver la taza", "Esta temporada."):
        assert texto in html


def test_aviso_de_temporada_aparece_en_todas_las_paginas(client, taza):
    temporada()
    assert "El pretexto: regreso a clases." in client.get(reverse("catalogo:ayuda")).content.decode()


def test_temporada_inactiva_no_se_muestra(client):
    temporada(activa=False)
    assert Temporada.actual() is None
    assert client.get("/temporada/regreso-a-clases/").status_code == 404


@pytest.mark.parametrize("dias_inicio, dias_fin, vigente", [
    (-1, 1, True), (1, 5, False), (-5, -1, False), (None, 1, True), (-1, None, True),
])
def test_temporada_entra_y_sale_por_fechas(dias_inicio, dias_fin, vigente):
    hoy = timezone.localdate()
    fecha = lambda dias: None if dias is None else hoy + datetime.timedelta(days=dias)  # noqa: E731
    temporada(inicio=fecha(dias_inicio), fin=fecha(dias_fin))
    assert (Temporada.actual() is not None) is vigente


def test_si_coinciden_gana_la_de_menor_orden():
    temporada(orden=2)
    primera = temporada(nombre="Buen Fin", slug="buen-fin", orden=1)
    assert Temporada.actual() == primera


def test_pagina_de_temporada_lista_solo_sus_productos(client, taza):
    otra = Producto.objects.create(categoria=taza.categoria, nombre="Plato", slug="plato", precio_base=Decimal("1"))
    t = temporada()
    t.productos.add(taza)
    html = client.get(t.get_absolute_url()).content.decode()
    assert "Taza de barro" in html and otra.nombre not in html


def test_al_terminar_la_temporada_el_producto_sigue_en_catalogo(client, taza):
    t = temporada()
    t.productos.add(taza)
    Temporada.objects.filter(pk=t.pk).update(activa=False)
    assert "Taza de barro" in client.get(reverse("catalogo:lista")).content.decode()


def test_guia_de_tallas_por_categoria(client, taza):
    assert "Guía de tallas" not in client.get(taza.get_absolute_url()).content.decode()
    Variante.objects.create(producto=taza, talla="M", existencias=1)
    Categoria.objects.filter(pk=taza.categoria_id).update(guia_tallas="M: 300 ml")
    html = client.get(taza.get_absolute_url()).content.decode()
    assert "Guía de tallas" in html and "M: 300 ml" in html


def test_muchas_categorias_no_rompen_el_menu(client):
    for i in range(12):
        Categoria.objects.create(nombre=f"Categoría {i}", slug=f"categoria-{i}")
    assert client.get(reverse("catalogo:inicio")).status_code == 200
