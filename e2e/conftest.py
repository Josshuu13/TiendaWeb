"""
Configuración de las pruebas en navegador (Playwright).

Se corren aparte, porque abren un navegador real y tardan más:

    pytest -m e2e

Con GUARDAR_CAPTURAS=1 guardan capturas de cada paso en docs/capturas/, que sirven
como evidencia de la entrega.
"""
import os
from pathlib import Path

import pytest
from django.core.management import call_command

# Playwright maneja su propio ciclo de eventos en este hilo. Esta variable le permite a
# Django usar la base de datos de prueba al mismo tiempo; solo aplica a estas pruebas.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

CAPTURAS = Path(__file__).resolve().parent.parent / "docs" / "capturas"


@pytest.fixture(scope="session")
def navegador():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        chromium = p.chromium.launch()
        yield chromium
        chromium.close()


@pytest.fixture
def tienda(live_server):
    """Servidor real con el catálogo de ejemplo cargado."""
    call_command("cargar_datos_demo", verbosity=0)
    return live_server.url


def _nueva_pagina(navegador, ancho=1280, alto=900, movil=False):
    contexto = navegador.new_context(
        viewport={"width": ancho, "height": alto}, locale="es-MX", is_mobile=movil, has_touch=movil,
    )
    pagina = contexto.new_page()
    pagina.errores = []
    pagina.on("pageerror", lambda e: pagina.errores.append(str(e)))
    pagina.on("console", lambda m: pagina.errores.append(m.text) if m.type == "error" else None)
    return contexto, pagina


@pytest.fixture
def pagina(navegador):
    contexto, pagina = _nueva_pagina(navegador)
    yield pagina
    contexto.close()


@pytest.fixture
def otra_pagina(navegador):
    """Segundo navegador independiente (por ejemplo, el del administrador)."""
    contexto, pagina = _nueva_pagina(navegador)
    yield pagina
    contexto.close()


@pytest.fixture
def pagina_movil(navegador):
    contexto, pagina = _nueva_pagina(navegador, 390, 844, movil=True)
    yield pagina
    contexto.close()


@pytest.fixture
def captura():
    """Guarda una captura solo si GUARDAR_CAPTURAS=1."""
    def guardar(pagina, nombre, completa=False):
        if os.environ.get("GUARDAR_CAPTURAS") == "1":
            CAPTURAS.mkdir(parents=True, exist_ok=True)
            pagina.screenshot(path=str(CAPTURAS / f"{nombre}.png"), full_page=completa)
    return guardar
