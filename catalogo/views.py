import json

from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .cotizacion import ErrorCotizacion, cotizar
from .models import Categoria, Producto, Variante


def _productos_activos():
    return Producto.objects.filter(activo=True).select_related("categoria").prefetch_related(
        Prefetch("variantes", queryset=Variante.objects.filter(activa=True))
    )


def inicio(request):
    destacados = _productos_activos().filter(destacado=True)[:6]
    return render(request, "catalogo/inicio.html", {"destacados": destacados})


def lista(request, slug=None):
    categoria = None
    productos = _productos_activos()
    if slug:
        categoria = get_object_or_404(Categoria, slug=slug)
        productos = productos.filter(categoria=categoria)
    return render(
        request,
        "catalogo/lista.html",
        {"categoria": categoria, "productos": productos},
    )


def detalle(request, slug):
    producto = get_object_or_404(_productos_activos(), slug=slug)
    contexto = {"producto": producto}
    if producto.personalizable:
        contexto["partes"] = producto.partes.prefetch_related("colores").select_related(
            "color_inicial"
        )
        contexto["decoraciones"] = producto.decoraciones.filter(activa=True)
    else:
        contexto["variantes"] = producto.variantes.all()
    return render(request, "catalogo/detalle.html", contexto)


@require_POST
def api_cotizar(request):
    """Recibe la selección en JSON y devuelve el desglose calculado por el servidor."""
    try:
        datos = json.loads(request.body or "{}")
        cot = cotizar(datos)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON no válido."}, status=400)
    except ErrorCotizacion as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    return JsonResponse({"ok": True, **cot.como_dict()})
