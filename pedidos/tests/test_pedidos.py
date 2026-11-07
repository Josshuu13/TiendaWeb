"""Pruebas de compra, seguimiento y posventa, según el anteproyecto."""
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse

from catalogo.models import Producto, Variante
from conftest import DIRECCION, agregar, comprar, seleccion_calcetin, seleccion_mono, seleccion_sueter
from pedidos import servicios
from pedidos.models import ConfiguracionTienda, EventoPedido, Pedido, SolicitudPosventa

pytestmark = pytest.mark.django_db
Estado = Pedido.Estado


@pytest.fixture(autouse=True)
def datos(catalogo):
    pass


def existencias(slug="sueter-santa", talla="M"):
    return Variante.objects.get(producto__slug=slug, talla=talla).existencias


def avanzar_hasta(pedido, estado):
    """Lleva un pedido pagado hasta el estado indicado por el camino permitido."""
    pedido.transportista, pedido.numero_guia = "Paquetería Demo", "DEMO-1"
    pedido.telefono_transportista = "5511111111"
    pedido.save()
    for paso in Pedido.PASOS[1:]:
        pedido = servicios.cambiar_estado(pedido, paso)
        if paso == estado:
            break
    return pedido


@pytest.fixture
def pagado(cliente):
    pedido = comprar(cliente, seleccion_sueter())
    servicios.confirmar_pago(pedido, "simulado")
    pedido.refresh_from_db()
    return pedido


# --- Compra ---

def test_compra_exige_iniciar_sesion(client):
    agregar(client, seleccion_sueter())
    r = client.get(reverse("pedidos:compra"))
    assert r.status_code == 302 and reverse("cuentas:entrar") in r.url and "next=" in r.url


def test_el_carrito_sobrevive_al_iniciar_sesion(client, usuario):
    agregar(client, seleccion_sueter())
    client.post(reverse("cuentas:entrar"), {"username": usuario.email, "password": "clave-de-prueba-123"})
    assert client.get(reverse("pedidos:compra")).status_code == 200


def test_compra_con_carrito_vacio_regresa_al_carrito(cliente):
    assert cliente.get(reverse("pedidos:compra")).url == reverse("carrito:ver")


def test_compra_crea_pedido_con_importes_del_servidor(cliente):
    envio = ConfiguracionTienda.cargar().costo_envio
    antes = existencias()
    pedido = comprar(cliente, seleccion_sueter(cantidad=2))
    assert pedido.folio.startswith("PR-") and len(pedido.folio) == 11
    assert pedido.estado == Estado.PENDIENTE_PAGO
    assert pedido.subtotal == Decimal("960.00")
    assert pedido.total == Decimal("960.00") + envio
    assert existencias() == antes - 2
    assert cliente.session["carrito"] == []


def test_direccion_invalida_no_crea_pedido(cliente):
    agregar(cliente, seleccion_sueter())
    r = cliente.post(reverse("pedidos:compra"), {**DIRECCION, "telefono": "123", "codigo_postal": "abc"})
    assert r.status_code == 200 and Pedido.objects.count() == 0


def test_el_costo_de_envio_se_edita_desde_la_configuracion(cliente):
    ConfiguracionTienda.objects.update_or_create(pk=1, defaults={"costo_envio": Decimal("150.00")})
    assert comprar(cliente, seleccion_sueter()).costo_envio == Decimal("150.00")


def test_pedido_mixto_con_las_tres_lineas_toma_el_mas_tardado(cliente, settings):
    settings.DIAS_ENVIO = 3
    pedido = comprar(cliente, seleccion_mono(), seleccion_sueter(), seleccion_calcetin())
    assert pedido.lineas.count() == 3
    resumen_dias = max(linea.producto.dias_elaboracion for linea in pedido.lineas.all())
    assert resumen_dias == 3
    from catalogo.entregas import rango_entrega
    assert (pedido.entrega_minima, pedido.entrega_maxima) == rango_entrega(3)


def test_la_personalizacion_se_conserva_aunque_cambie_el_catalogo(cliente):
    pedido = comprar(cliente, seleccion_mono())
    linea = pedido.lineas.get()
    assert linea.seleccion["Patas"] == "Rojo navidad"
    assert len(linea.seleccion) == 6 and len(linea.opciones) == 6
    Producto.objects.filter(slug="mono-clasico").update(precio_base=Decimal("999.00"), nombre="Otro")
    linea.refresh_from_db()
    assert linea.precio_unitario == Decimal("120.00") and linea.nombre == "Moño clásico personalizable"


def test_si_se_agota_mientras_compra_no_se_crea_nada(cliente):
    agregar(cliente, seleccion_sueter(cantidad=2))
    Variante.objects.filter(producto__slug="sueter-santa", talla="M").update(existencias=1)
    r = cliente.post(reverse("pedidos:compra"), DIRECCION)
    assert r.url == reverse("carrito:ver")
    assert Pedido.objects.count() == 0


def test_dos_compras_no_pueden_vender_la_ultima_pieza(cliente, usuario):
    """La condición de existencias está en el UPDATE; se prueba el servicio directamente."""
    from carrito.carrito import Carrito
    agregar(cliente, seleccion_sueter(cantidad=1))
    resumen = Carrito(cliente.session).resumen()
    Variante.objects.filter(producto__slug="sueter-santa", talla="M").update(existencias=1)
    servicios.crear_pedido(usuario, resumen, DIRECCION)
    with pytest.raises(servicios.ErrorPedido):
        servicios.crear_pedido(usuario, resumen, DIRECCION)
    assert existencias() == 0 and Pedido.objects.count() == 1


# --- Cada cliente solo ve lo suyo ---

@pytest.mark.parametrize("nombre, metodo", [
    ("pedidos:detalle", "get"), ("pedidos:pagar", "post"), ("pedidos:descartar", "post"),
    ("pedidos:solicitud", "post"), ("pedidos:pago_simulado", "get"),
])
def test_un_pedido_ajeno_responde_404(client, pagado, otro_usuario, nombre, metodo):
    client.force_login(otro_usuario)
    assert getattr(client, metodo)(reverse(nombre, args=[pagado.folio])).status_code == 404


def test_mis_pedidos_solo_muestra_los_propios(client, pagado, otro_usuario):
    client.force_login(otro_usuario)
    assert pagado.folio not in client.get(reverse("pedidos:lista")).content.decode()


def test_mis_pedidos_exige_iniciar_sesion(client):
    assert client.get(reverse("pedidos:lista")).status_code == 302


# --- Pago simulado ---

def test_pago_simulado_confirma_el_pedido(cliente):
    pedido = comprar(cliente, seleccion_sueter())
    cliente.post(reverse("pedidos:pago_simulado", args=[pedido.folio]), {"resultado": "aprobar"})
    pedido.refresh_from_db()
    assert pedido.estado == Estado.CONFIRMADO and pedido.pagado_en


def test_pago_rechazado_deja_el_pedido_pendiente(cliente):
    pedido = comprar(cliente, seleccion_sueter())
    cliente.post(reverse("pedidos:pago_simulado", args=[pedido.folio]), {"resultado": "rechazar"})
    pedido.refresh_from_db()
    assert pedido.estado == Estado.PENDIENTE_PAGO


def test_pago_simulado_no_existe_en_produccion(cliente, settings):
    pedido = comprar(cliente, seleccion_sueter())
    settings.PAGO_SIMULADO = False
    assert cliente.get(reverse("pedidos:pago_simulado", args=[pedido.folio])).status_code == 404


def test_confirmacion_repetida_no_duplica_nada(cliente):
    pedido = comprar(cliente, seleccion_sueter())
    assert servicios.confirmar_pago(pedido, "a") is True
    assert servicios.confirmar_pago(pedido, "b") is False
    pedido.refresh_from_db()
    assert pedido.referencia_pago == "a"
    assert pedido.eventos.filter(estado=Estado.CONFIRMADO).count() == 1


def test_abandonar_un_pedido_sin_pagar_libera_las_piezas(cliente):
    antes = existencias()
    pedido = comprar(cliente, seleccion_sueter(cantidad=2))
    cliente.post(reverse("pedidos:descartar", args=[pedido.folio]))
    pedido.refresh_from_db()
    assert pedido.estado == Estado.CANCELADO and existencias() == antes


# --- Estados y seguimiento ---

def test_no_se_puede_saltar_de_estado(pagado):
    with pytest.raises(servicios.ErrorPedido, match="No se puede pasar"):
        servicios.cambiar_estado(pagado, Estado.ENTREGADO)


def test_enviar_exige_transportista_y_guia(pagado):
    servicios.cambiar_estado(pagado, Estado.EN_PREPARACION)
    with pytest.raises(servicios.ErrorPedido, match="transportista"):
        servicios.cambiar_estado(pagado, Estado.ENVIADO)


def test_linea_de_tiempo_marca_el_paso_actual(pagado):
    pedido = avanzar_hasta(pagado, Estado.ENVIADO)
    pasos = pedido.linea_de_tiempo
    assert [p["hecho"] for p in pasos] == [True, True, True, False, False]
    assert [p["nombre"] for p in pasos if p["actual"]] == ["Enviado"]
    assert pasos[2]["fecha"] is not None


def test_pagina_de_seguimiento_muestra_folio_transportista_y_guia(cliente, pagado):
    avanzar_hasta(pagado, Estado.ENVIADO)
    html = cliente.get(pagado.get_absolute_url()).content.decode()
    for texto in (pagado.folio, "Paquetería Demo", "DEMO-1", "Seguimiento de tu entrega"):
        assert texto in html


def test_antes_de_salir_no_se_muestra_el_transportista(cliente, pagado):
    pagado.transportista = "Paquetería Demo"
    pagado.save()
    assert "Paquetería Demo" not in cliente.get(pagado.get_absolute_url()).content.decode()


@pytest.mark.parametrize("estado, visible", [
    (Estado.EN_PREPARACION, False), (Estado.ENVIADO, False), (Estado.EN_CAMINO, True), (Estado.ENTREGADO, False),
])
def test_telefono_del_transportista_solo_mientras_va_en_camino(cliente, pagado, estado, visible):
    avanzar_hasta(pagado, estado)
    assert ("55 1111 1111" in cliente.get(pagado.get_absolute_url()).content.decode()) is visible


def test_soporte_siempre_visible_y_whatsapp_con_id_de_pedido(cliente, pagado):
    html = cliente.get(pagado.get_absolute_url()).content.decode()
    assert "55 0000 0000" in html
    assert f"wa.me/525500000000?text=Hola%2C%20necesito%20ayuda%20con%20mi%20pedido%20{pagado.folio}" in html


def test_whatsapp_se_cambia_desde_la_configuracion(client):
    ConfiguracionTienda.objects.update_or_create(pk=1, defaults={"whatsapp": "5599998888"})
    assert "wa.me/525599998888" in client.get(reverse("catalogo:ayuda")).content.decode()


def test_correo_al_cambiar_de_estado(cliente, django_capture_on_commit_callbacks):
    pedido = comprar(cliente, seleccion_sueter())
    with django_capture_on_commit_callbacks(execute=True):
        servicios.confirmar_pago(pedido, "simulado")
    assert len(mail.outbox) == 1
    assert pedido.folio in mail.outbox[0].subject and "Confirmado" in mail.outbox[0].subject


# --- Cancelación y devolución ---

def test_cancelacion_aprobada_repone_existencias(cliente, pagado):
    antes = existencias()
    cliente.post(reverse("pedidos:solicitud", args=[pagado.folio]),
                 {"tipo": "cancelacion", "motivo": "Me equivoqué de talla"})
    solicitud = SolicitudPosventa.objects.get()
    assert solicitud.estado == "solicitada"
    servicios.resolver_solicitud(solicitud, True, "Aprobada")
    pagado.refresh_from_db()
    assert pagado.estado == Estado.CANCELADO and existencias() == antes + 1


def test_solicitud_rechazada_no_cambia_el_pedido(pagado):
    solicitud = servicios.crear_solicitud(pagado, "cancelacion", "Motivo")
    servicios.resolver_solicitud(solicitud, False, "No procede")
    pagado.refresh_from_db()
    assert pagado.estado == Estado.CONFIRMADO


def test_no_se_cancela_en_preparacion(pagado):
    pedido = servicios.cambiar_estado(pagado, Estado.EN_PREPARACION)
    with pytest.raises(servicios.ErrorPedido, match="ya no se puede cancelar"):
        servicios.crear_solicitud(pedido, "cancelacion", "Motivo")


def test_solicitud_aprobada_tarde_no_reembolsa(pagado, monkeypatch):
    """Si el pedido avanzó mientras se revisaba, no se toca el dinero."""
    llamadas = []
    monkeypatch.setattr("pedidos.pagos.reembolsar", lambda pedido: llamadas.append(pedido))
    solicitud = servicios.crear_solicitud(pagado, "cancelacion", "Motivo")
    servicios.cambiar_estado(pagado, Estado.EN_PREPARACION)
    with pytest.raises(servicios.ErrorPedido):
        servicios.resolver_solicitud(solicitud, True)
    solicitud.refresh_from_db()
    assert llamadas == [] and solicitud.estado == "solicitada"


def test_devolucion_solo_despues_de_entregado(pagado):
    with pytest.raises(servicios.ErrorPedido, match="entregados"):
        servicios.crear_solicitud(pagado, "devolucion", "Motivo")
    pedido = avanzar_hasta(pagado, Estado.ENTREGADO)
    solicitud = servicios.crear_solicitud(pedido, "devolucion", "Llegó mal")
    servicios.resolver_solicitud(solicitud, True)
    pedido.refresh_from_db()
    assert pedido.estado == Estado.DEVUELTO


def test_no_se_duplica_una_solicitud_abierta(pagado):
    servicios.crear_solicitud(pagado, "cancelacion", "Motivo")
    with pytest.raises(servicios.ErrorPedido, match="en revisión"):
        servicios.crear_solicitud(pagado, "cancelacion", "Otra vez")


def test_solicitud_sin_motivo_no_se_registra(cliente, pagado):
    cliente.post(reverse("pedidos:solicitud", args=[pagado.folio]), {"tipo": "cancelacion", "motivo": ""})
    assert SolicitudPosventa.objects.count() == 0


# --- Administración ---

@pytest.fixture
def admin_cliente(client, pagado):
    """Se usa después de `pagado`: la misma sesión pasa a ser del administrador."""
    client.force_login(get_user_model().objects.create_superuser("admin", "admin@example.com", "clave-de-prueba-123"))
    return client


def datos_admin(pedido, **cambios):
    return {
        "estado": pedido.estado, "transportista": pedido.transportista, "numero_guia": pedido.numero_guia,
        "telefono_transportista": pedido.telefono_transportista,
        "lineas-TOTAL_FORMS": 0, "lineas-INITIAL_FORMS": 0,
        "eventos-TOTAL_FORMS": 0, "eventos-INITIAL_FORMS": 0,
        "solicitudes-TOTAL_FORMS": 0, "solicitudes-INITIAL_FORMS": 0,
        **cambios,
    }


def test_admin_cambia_estado_y_captura_envio(admin_cliente, pagado):
    url = reverse("admin:pedidos_pedido_change", args=[pagado.pk])
    r = admin_cliente.post(url, datos_admin(pagado, estado="en_preparacion"))
    assert r.status_code == 302
    r = admin_cliente.post(url, datos_admin(
        Pedido.objects.get(pk=pagado.pk), estado="enviado",
        transportista="Paquetería Demo", numero_guia="G-1", telefono_transportista="5511111111",
    ))
    assert r.status_code == 302
    pagado.refresh_from_db()
    assert pagado.estado == Estado.ENVIADO and pagado.numero_guia == "G-1"
    assert EventoPedido.objects.filter(pedido=pagado, estado="enviado").exists()


def test_admin_no_puede_saltar_de_estado(admin_cliente, pagado):
    url = reverse("admin:pedidos_pedido_change", args=[pagado.pk])
    r = admin_cliente.post(url, datos_admin(pagado, estado="entregado"))
    assert r.status_code == 200  # el formulario regresa con error
    pagado.refresh_from_db()
    assert pagado.estado == Estado.CONFIRMADO


def test_cliente_normal_no_entra_al_admin(cliente):
    r = cliente.get(reverse("admin:pedidos_pedido_changelist"))
    assert r.status_code == 302 and "/admin/login/" in r.url


def test_admin_aprueba_solicitud_con_accion(admin_cliente, pagado):
    servicios.crear_solicitud(pagado, "cancelacion", "Motivo")
    solicitud = SolicitudPosventa.objects.get()
    admin_cliente.post(reverse("admin:pedidos_solicitudposventa_changelist"), {
        "action": "aprobar", "_selected_action": [solicitud.pk],
    })
    pagado.refresh_from_db()
    assert pagado.estado == Estado.CANCELADO


def test_accion_de_transportista_de_prueba(admin_cliente, pagado):
    admin_cliente.post(reverse("admin:pedidos_pedido_changelist"), {
        "action": "asignar_transportista_demo", "_selected_action": [pagado.pk],
    })
    pagado.refresh_from_db()
    assert pagado.transportista == "Paquetería Demo" and pagado.numero_guia.startswith("DEMO-")


@pytest.mark.parametrize("nombre", [
    "admin:pedidos_pedido_changelist", "admin:pedidos_solicitudposventa_changelist",
    "admin:pedidos_configuraciontienda_changelist", "admin:pedidos_eventopago_changelist",
])
def test_paginas_del_admin_cargan(admin_cliente, nombre):
    assert admin_cliente.get(reverse(nombre)).status_code == 200


def test_ficha_del_pedido_en_admin_carga(admin_cliente, pagado):
    assert admin_cliente.get(reverse("admin:pedidos_pedido_change", args=[pagado.pk])).status_code == 200
