"""
Vistas del carrito.

Los formularios funcionan aunque falle JavaScript: con HTMX se reemplaza solo el
contenido del carrito y, sin HTMX, el navegador recarga la página completa.
"""
import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from catalogo.cotizacion import ErrorCotizacion
from pedidos.models import ConfiguracionTienda

from .carrito import Carrito


def _contexto(request, carrito, aviso=""):
    costo_envio = ConfiguracionTienda.cargar().costo_envio
    return {"resumen": carrito.resumen(costo_envio), "aviso": aviso}


def _responder(request, carrito, aviso=""):
    """Con HTMX devuelve solo el contenido y avisa que cambió el contador."""
    if request.headers.get("HX-Request"):
        respuesta = render(request, "carrito/_contenido.html", _contexto(request, carrito, aviso))
        respuesta["HX-Trigger"] = "carrito-cambiado"
        return respuesta
    return redirect("carrito:ver")


@require_GET
def ver(request):
    return render(request, "carrito/ver.html", _contexto(request, Carrito(request.session)))


@require_POST
def agregar(request):
    """Recibe la selección en JSON, igual que la cotización."""
    carrito = Carrito(request.session)
    try:
        carrito.agregar(json.loads(request.body or "{}"))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON no válido."}, status=400)
    except ErrorCotizacion as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    return JsonResponse({"ok": True, "piezas": carrito.piezas})


@require_POST
def actualizar(request, linea_id):
    carrito = Carrito(request.session)
    aviso = ""
    try:
        carrito.cambiar_cantidad(linea_id, request.POST.get("cantidad"))
    except ErrorCotizacion as e:
        aviso = str(e)
    return _responder(request, carrito, aviso)


@require_POST
def quitar(request, linea_id):
    carrito = Carrito(request.session)
    carrito.quitar(linea_id)
    return _responder(request, carrito)


@require_GET
def contador(request):
    return render(request, "carrito/_contador.html")
