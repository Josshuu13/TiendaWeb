"""
Pruebas de la cotización validada en el servidor y de las páginas.

Antes de cada prueba se carga el catálogo de ejemplo en una base de datos
temporal (pytest la crea y la borra sola).
"""
import json
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.urls import reverse

from catalogo.cotizacion import ErrorCotizacion, cotizar
from catalogo.models import Color, Combinacion, Estampado, Parte, Producto, Variante

pytestmark = pytest.mark.django_db

PARTES = ["patas", "baseabajo", "basearriba", "decorado", "tiras", "nudo"]


@pytest.fixture(autouse=True)
def catalogo_demo():
    call_command("cargar_datos_demo", verbosity=0)


def color(nombre):
    """Id de un color por su nombre."""
    return Color.objects.get(nombre=nombre).pk


def mono(cantidad=1, **cambios):
    """Selección completa del moño: todas las partes en Rojo navidad, salvo cambios."""
    opciones = {p: color("Rojo navidad") for p in PARTES}
    opciones.update(cambios)
    return {"producto": "mono-clasico", "opciones": opciones, "cantidad": cantidad}


# --- Estructura del moño ---

def test_mono_tiene_seis_partes_en_orden():
    claves = list(Parte.objects.filter(producto__slug="mono-clasico").values_list("clave", flat=True))
    assert claves == PARTES


def test_pasos_del_cliente_en_orden():
    """El cliente elige: Patas, Base superior, Base inferior, Decorado, Tiras, Nudo."""
    nombres = list(Parte.objects.filter(producto__slug="mono-clasico")
                   .order_by("paso").values_list("nombre", flat=True))
    assert nombres == ["Patas", "Base superior", "Base inferior", "Decorado", "Tiras", "Nudo"]


def test_combinaciones_tienen_las_seis_partes_y_se_pueden_cotizar():
    for combo in Combinacion.objects.filter(activa=True):
        datos = combo.como_dict()
        assert set(datos["colores"]) == set(PARTES)
        cot = cotizar({"producto": "mono-clasico", "opciones": datos["colores"], "cantidad": 1})
        assert cot.precio_unitario == Decimal("85.00")


def test_solo_el_decorado_admite_estampado():
    estampables = Parte.objects.filter(admite_estampado=True).values_list("clave", flat=True)
    assert list(estampables) == ["decorado"]


def test_paleta_incluye_colores_nuevos():
    for nombre in ["Jade", "Naranja", "Palo de rosa", "Café arena", "Azul turquesa"]:
        assert Color.objects.get(nombre=nombre).activo


def test_mono_se_puede_cotizar_con_un_color_nuevo():
    cot = cotizar(mono(patas=color("Jade"), nudo=color("Palo de rosa")))
    assert cot.seleccion["Patas"] == "Jade"


def test_pagina_del_mono_ofrece_pedir_otro_color(client):
    html = client.get(reverse("catalogo:producto", args=["mono-clasico"])).content.decode()
    assert "¿No encuentras tu color?" in html and "wa.me/52" in html


def test_paleta_tiene_colores_escolares_y_navidenos():
    assert Color.objects.filter(grupo=Color.ESCOLAR, activo=True).count() >= 8
    assert Color.objects.filter(grupo=Color.NAVIDENO, activo=True).count() >= 5


# --- Moño personalizable ---

def test_mono_liso_cuesta_el_precio_base():
    cot = cotizar(mono(baseabajo=color("Blanco"), nudo=color("Verde pino")))
    assert cot.precio_unitario == Decimal("85.00")
    assert cot.seleccion["Base inferior"] == "Blanco"
    assert cot.seleccion["Nudo"] == "Verde pino"


def test_estampado_suma_precio_y_reemplaza_color_del_decorado():
    datos = mono(cantidad=2, estampado="tejido-rojo")
    del datos["opciones"]["decorado"]  # con estampado, el decorado no necesita color
    cot = cotizar(datos)
    assert cot.precio_unitario == Decimal("110.00")  # 85 + 25
    assert cot.total == Decimal("220.00")
    assert cot.seleccion["Decorado"] == "Estampado: Tejido rojo"


def test_estampado_inactivo_se_rechaza():
    Estampado.objects.filter(clave="rombos-verde").update(activo=False)
    with pytest.raises(ErrorCotizacion, match="estampado"):
        cotizar(mono(estampado="rombos-verde"))


def test_falta_color_de_una_parte():
    datos = mono()
    del datos["opciones"]["tiras"]
    with pytest.raises(ErrorCotizacion, match="tiras"):
        cotizar(datos)


def test_color_inactivo_se_rechaza():
    Color.objects.filter(nombre="Negro").update(activo=False)
    with pytest.raises(ErrorCotizacion):
        cotizar(mono(nudo=color("Negro")))


def test_opcion_inventada_se_rechaza():
    with pytest.raises(ErrorCotizacion, match="no reconocidas"):
        cotizar(mono(precio=1))


@pytest.mark.parametrize("cantidad", [0, -2, 51, "muchos"])
def test_cantidad_fuera_de_rango(cantidad):
    with pytest.raises(ErrorCotizacion):
        cotizar(mono(cantidad=cantidad))


# --- Productos de catálogo ---

def test_sueter_talla_grande_tiene_extra():
    v = Variante.objects.get(producto__slug="sueter-renos-azul", talla="G", color__nombre="Azul marino")
    cot = cotizar({"producto": "sueter-renos-azul", "variante": v.sku, "cantidad": 2})
    assert cot.precio_unitario == Decimal("490.00")
    assert cot.total == Decimal("980.00")


def test_variante_agotada():
    v = Variante.objects.get(producto__slug="mono-guinda-clasico")
    v.existencias = 0
    v.save()
    with pytest.raises(ErrorCotizacion, match="agotada"):
        cotizar({"producto": "mono-guinda-clasico", "variante": v.sku})


def test_no_se_puede_pedir_mas_de_lo_que_hay():
    v = Variante.objects.filter(producto__slug="calcetines-santa").first()
    with pytest.raises(ErrorCotizacion, match="Solo quedan"):
        cotizar({"producto": "calcetines-santa", "variante": v.sku, "cantidad": v.existencias + 1})


def test_variante_de_otro_producto_se_rechaza():
    ajena = Variante.objects.filter(producto__slug="sueter-santa").first()
    with pytest.raises(ErrorCotizacion):
        cotizar({"producto": "sueter-renos-azul", "variante": ajena.sku})


def test_producto_inactivo_no_se_cotiza():
    Producto.objects.filter(slug="sueter-renos-azul").update(activo=False)
    with pytest.raises(ErrorCotizacion):
        cotizar({"producto": "sueter-renos-azul", "variante": "X"})


def test_cargar_datos_demo_se_puede_repetir():
    call_command("cargar_datos_demo", verbosity=0)  # segunda vez: no debe duplicar
    assert Parte.objects.filter(producto__slug="mono-clasico").count() == 6
    assert Estampado.objects.count() == 2
    assert Producto.objects.filter(categoria__slug="kits").count() == 4


# --- API y páginas ---

def test_api_devuelve_desglose(client):
    datos = mono(estampado="rombos-verde")
    r = client.post(reverse("catalogo:api_cotizar"), json.dumps(datos), content_type="application/json")
    assert r.status_code == 200
    assert r.json()["total"] == "110.00"


def test_api_ignora_precio_enviado_por_el_cliente(client):
    datos = mono()
    datos["total"] = "1.00"
    r = client.post(reverse("catalogo:api_cotizar"), json.dumps(datos), content_type="application/json")
    assert r.json()["total"] == "85.00"


def test_api_error_es_400(client):
    r = client.post(reverse("catalogo:api_cotizar"), "{malo", content_type="application/json")
    assert r.status_code == 400


def test_pagina_del_mono_incluye_simulador(client):
    r = client.get(reverse("catalogo:producto", args=["mono-clasico"]))
    html = r.content.decode()
    assert 'id="simulador"' in html
    assert "config-simulador" in html
    assert "simulador/mono-clasico/decorado.png" in html
    assert "Lo más vendido" in html
    assert "Siguiente: Base superior" in html


@pytest.mark.parametrize("nombre, args", [
    ("catalogo:inicio", []),
    ("catalogo:lista", []),
    ("catalogo:categoria", ["sueteres"]),
    ("catalogo:producto", ["mono-clasico"]),
    ("catalogo:producto", ["calcetines-rayas"]),
    ("catalogo:producto", ["kit-reno-rojo"]),
    ("catalogo:categoria", ["kits"]),
    ("catalogo:ayuda", []),
])
def test_paginas_cargan(client, nombre, args):
    assert client.get(reverse(nombre, args=args)).status_code == 200


# --- Diseños listos para usar (moños de uniforme) ---

def test_disenos_listos_se_venden_sin_selector_de_color():
    from catalogo.management.commands.cargar_datos_demo import DISENOS_LISTOS
    for slug, _nombre, _partes in DISENOS_LISTOS:
        p = Producto.objects.get(slug=slug)
        assert p.activo and not p.personalizable
        assert p.url_imagen_estatica                  # su imagen existe en static/img/monos
        v = p.variantes.get()                          # una sola variante...
        assert v.color is None and v.existencias > 0   # ...sin color y con existencias
    assert not Producto.objects.filter(slug="mono-escolar", activo=True).exists()  # el viejo se retira


def test_dos_colores_reparte_las_partes_como_se_acordo():
    from catalogo.management.commands.cargar_datos_demo import dos_colores
    partes = dos_colores("Celeste", "Gris Oxford")
    assert {k for k, c in partes.items() if c == "Celeste"} == {"basearriba", "patas", "tiras", "nudo"}
    assert {k for k, c in partes.items() if c == "Gris Oxford"} == {"baseabajo", "decorado"}


def test_cotizar_diseno_listo():
    v = Variante.objects.get(producto__slug="mono-rojo-con-azul-marino")
    cot = cotizar({"producto": "mono-rojo-con-azul-marino", "variante": v.sku, "cantidad": 2})
    assert cot.total == Decimal("170.00")


def test_pagina_de_monos_tiene_disena_el_tuyo_y_disenos_listos(client):
    html = client.get(reverse("catalogo:categoria", args=["monos"])).content.decode()
    assert "¿Buscas un color en especial?" in html and "Diseños listos para usar." in html
    assert "Personalizar" in html
    assert "filtro-color" not in html                  # sin filtro de color en Moños
    # El personalizable sale una sola vez (en "Diseña el tuyo"), no también como tarjeta.
    assert html.count('href="/producto/mono-clasico/" class="prod"') == 0
    # Los diseños salen en el orden de DISENOS_LISTOS.
    assert html.index("Moño azul marino clásico") < html.index("Moño rojo, blanco y azul marino")


def test_generar_imagenes_monos(tmp_path):
    from catalogo.management.commands.cargar_datos_demo import DISENOS_LISTOS
    call_command("generar_imagenes_monos", destino=str(tmp_path))
    assert sorted(f.name for f in tmp_path.iterdir()) == sorted(f"{d[0]}.webp" for d in DISENOS_LISTOS)
