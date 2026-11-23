"""
Recorrido completo en un navegador real, como lo haría un cliente.

Cubre los criterios de aceptación del anteproyecto: compra con las tres líneas de producto,
personalización visible y conservada, importe calculado, pago de prueba, fecha propuesta y
solicitud de cancelación que el administrador resuelve.
"""
import re
import secrets

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import expect

pytestmark = [pytest.mark.e2e, pytest.mark.django_db(transaction=True)]


def agregar_al_carrito(pagina, piezas):
    pagina.click("#btn-carrito")
    expect(pagina.locator("#aviso-carrito")).to_be_visible()
    expect(pagina.locator("#contador-carrito b")).to_have_text(str(piezas))


def comprar_en_navegador(pagina, tienda, captura=lambda *a, **k: None, completa=True):
    """Arma un carrito, crea la cuenta, paga y devuelve el folio del pedido."""
    piezas = 0
    if completa:
        # 1) Moño personalizado en el simulador.
        pagina.goto(f"{tienda}/producto/mono-clasico/")
        expect(pagina.locator("#simulador-cargando")).to_have_count(0, timeout=15000)
        captura(pagina, "03-simulador-mono")
        piezas += 1
        agregar_al_carrito(pagina, piezas)

        # 2) Calceta personalizada: diseño, tamaño y posición.
        pagina.goto(f"{tienda}/producto/calcetas-personalizables/")
        pagina.click("label[for='diseno-pino']")
        pagina.locator("#calceta-tamano").fill("120")
        pagina.locator("#calceta-y").fill("60")
        expect(pagina.locator("#cotizacion-cuerpo")).to_contain_text("$119.00")  # 99 + 20 del pino
        captura(pagina, "04-personalizador-calceta")
        piezas += 1
        agregar_al_carrito(pagina, piezas)

        # 3) Calcetines de catálogo.
        pagina.goto(f"{tienda}/producto/calcetines-santa-claus/")
        piezas += 1
        agregar_al_carrito(pagina, piezas)

    # 4) Suéter con talla.
    pagina.goto(f"{tienda}/producto/sueter-santa/")
    pagina.click(".talla-boton:has-text('Mediana')")
    piezas += 1
    agregar_al_carrito(pagina, piezas)

    # Carrito: vista previa de lo personalizado y fecha estimada.
    pagina.goto(f"{tienda}/carrito/")
    expect(pagina.locator(".resumen-entrega, .panel").first).to_be_visible()
    if completa:
        expect(pagina.locator("img[alt='Vista previa de tu moño']")).to_have_count(2)
        expect(pagina.get_by_text("Diseño: Pino")).to_be_visible()
    expect(pagina.get_by_text(re.compile("Si pides hoy, llega entre"))).to_be_visible()
    captura(pagina, "05-carrito", completa=True)

    # Cuenta nueva desde el carrito.
    pagina.click("text=Continuar con la compra")
    pagina.click("text=Crea una")
    clave = secrets.token_urlsafe(12)
    pagina.fill("#id_first_name", "Ana")
    pagina.fill("#id_email", f"ana.{secrets.token_hex(3)}@example.com")
    pagina.fill("#id_password1", clave)
    pagina.fill("#id_password2", clave)
    pagina.click("button:has-text('Crear cuenta')")

    # Dirección y pago de prueba.
    expect(pagina).to_have_url(re.compile("/compra/$"))
    pagina.fill("#id_telefono", "5512345678")
    pagina.fill("#id_calle", "Av. Universidad 3000")
    pagina.fill("#id_colonia", "Copilco")
    pagina.fill("#id_codigo_postal", "04510")
    pagina.fill("#id_ciudad", "Coyoacán")
    pagina.select_option("#id_entidad", "Ciudad de México")
    captura(pagina, "06-finalizar-compra", completa=True)
    pagina.click("button:has-text('Ir a pagar')")
    pagina.click("button:has-text('Aprobar pago')")

    expect(pagina.locator(".etiqueta.estado-pedido")).to_have_text("Confirmado")
    folio = pagina.locator(".pedido-folio").first.inner_text()
    assert re.fullmatch(r"PR-[2-9A-Z]{8}", folio)
    return folio


def test_compra_completa_con_las_tres_lineas(pagina, tienda, captura):
    pagina.goto(tienda)
    expect(pagina.locator("h1")).to_have_text("Pretexto")
    captura(pagina, "01-portada")
    pagina.goto(f"{tienda}/catalogo/")
    captura(pagina, "02-catalogo")

    folio = comprar_en_navegador(pagina, tienda, captura)

    # El pedido conserva lo personalizado y muestra seguimiento, soporte e importes.
    expect(pagina.get_by_text("Seguimiento de tu entrega")).to_be_visible()
    expect(pagina.get_by_text("Diseño: Pino")).to_be_visible()
    expect(pagina.get_by_text("Tamaño: 120 %")).to_be_visible()
    expect(pagina.locator("a[href*='wa.me']").first).to_have_attribute("href", re.compile(folio))
    captura(pagina, "07-pedido-confirmado", completa=True)
    assert pagina.errores == [], pagina.errores


def test_cancelacion_solicitada_y_aprobada_en_el_admin(pagina, otra_pagina, tienda, captura):
    folio = comprar_en_navegador(pagina, tienda, completa=False)

    # El cliente solicita la cancelación.
    pagina.click("summary:has-text('Solicitar cancelación')")
    pagina.fill("#id_motivo", "Me equivoqué de talla.")
    pagina.click("button:has-text('Enviar solicitud')")
    expect(pagina.get_by_text("Cancelación en revisión")).to_be_visible()

    # El administrador la aprueba en su propio navegador.
    clave = secrets.token_urlsafe(12)
    get_user_model().objects.create_superuser("admin", "admin@example.com", clave)
    otra_pagina.goto(f"{tienda}/admin/pedidos/solicitudposventa/")
    otra_pagina.fill("#id_username", "admin")
    otra_pagina.fill("#id_password", clave)
    otra_pagina.click("input[type='submit']")
    otra_pagina.check("input[name='_selected_action']")
    otra_pagina.select_option("select[name='action']", "aprobar")
    captura(otra_pagina, "08-admin-solicitudes")
    otra_pagina.click("button[name='index']")
    expect(otra_pagina.get_by_text(f"{folio}: solicitud resuelta.")).to_be_visible()

    # El cliente ve su pedido cancelado.
    pagina.reload()
    expect(pagina.locator(".etiqueta.estado-pedido")).to_have_text("Cancelado")
    captura(pagina, "09-pedido-cancelado", completa=True)
    assert pagina.errores == [], pagina.errores


def test_la_tienda_se_usa_en_celular(pagina_movil, tienda, captura):
    pagina_movil.goto(tienda)
    captura(pagina_movil, "10-celular-portada")
    pagina_movil.goto(f"{tienda}/producto/calcetas-personalizables/")
    captura(pagina_movil, "11-celular-calceta")
    for ruta in ("/", "/catalogo/", "/producto/mono-clasico/", "/producto/calcetas-personalizables/", "/carrito/"):
        pagina_movil.goto(f"{tienda}{ruta}")
        ancho = pagina_movil.evaluate("document.documentElement.scrollWidth")
        assert ancho <= 390, f"{ruta} se sale de la pantalla ({ancho}px)"
    assert pagina_movil.errores == [], pagina_movil.errores
