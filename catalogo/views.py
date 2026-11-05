"""
Vistas: reciben la petición del navegador, consultan los modelos y responden.

inicio       -> portada con productos destacados.
lista        -> catálogo completo o filtrado por categoría.
detalle      -> página de un producto (simulador si es personalizable).
api_cotizar  -> recibe la selección en JSON y devuelve el precio calculado.
"""
import json

from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.views.decorators.http import require_POST

from .cotizacion import ErrorCotizacion, cotizar
from .models import Categoria, Color, Producto, Variante


def _productos_activos():
    """Consulta base: productos activos con su categoría y variantes ya cargadas
    (evita hacer una consulta a la base de datos por cada producto)."""
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


def _agrupar_colores(colores):
    """Ordena los colores de una parte por grupo (Escolares, Navideños, Básicos)
    para mostrarlos separados en la página."""
    grupos = []
    for clave, nombre in Color.GRUPOS:
        del_grupo = [c for c in colores if c.grupo == clave and c.activo]
        if del_grupo:
            grupos.append({"nombre": nombre, "colores": del_grupo})
    return grupos


def detalle(request, slug):
    producto = get_object_or_404(_productos_activos(), slug=slug)
    contexto = {"producto": producto}

    if producto.personalizable:
        # Partes en orden de dibujo (para el simulador)...
        partes = list(
            producto.partes.prefetch_related("colores").select_related("color_inicial")
        )
        # ...y en el orden de los pasos (para lo que ve el cliente).
        por_paso = sorted(partes, key=lambda p: (p.paso, p.orden))
        estampados = list(producto.estampados.filter(activo=True))
        combinaciones = producto.combinaciones.filter(activa=True).prefetch_related(
            "colores__parte", "colores__color"
        ).select_related("estampado")

        # Cada parte con su número de paso, el nombre de la siguiente parte
        # (para el botón "Siguiente: ...") y sus colores ya agrupados.
        contexto["partes"] = [
            {
                "parte": p,
                "numero": i,
                "siguiente": por_paso[i].nombre if i < len(por_paso) else "",
                "grupos": _agrupar_colores(list(p.colores.all())),
            }
            for i, p in enumerate(por_paso, start=1)
        ]
        contexto["total_pasos"] = len(por_paso)
        contexto["estampados"] = estampados
        contexto["combinaciones"] = [
            {"nombre": c.nombre,
             "puntos": [cp.color.codigo_hex for cp in sorted(c.colores.all(), key=lambda x: x.parte.paso)]}
            for c in combinaciones
        ]
        contexto["config_combinaciones"] = [c.como_dict() for c in combinaciones]

        # Configuración que lee el simulador (simulador.js) desde la página.
        contexto["config_simulador"] = {
            "capas": [{"clave": p.clave, "url": p.url_capa} for p in partes],
            "estampables": [p.clave for p in partes if p.admite_estampado],
            "mapa_estampado": static(f"{producto.carpeta_simulador}decorado-uv.png"),
            "estampados": {e.clave: e.url_imagen for e in estampados},
        }
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
