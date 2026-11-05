"""
Vistas: reciben la petición del navegador, consultan los modelos y responden.

inicio       -> portada: categorías, kits navideños y "Así de fácil".
lista        -> catálogo completo o por categoría, con filtros por talla y color.
ayuda        -> políticas de envío, cambios/devoluciones y cancelación.
detalle      -> página de un producto (simulador si es personalizable).
api_cotizar  -> recibe la selección en JSON y devuelve el precio calculado.
"""
import json

from django.conf import settings
from django.db.models import Prefetch
from django.utils.text import slugify
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.views.decorators.http import require_POST

from .cotizacion import ErrorCotizacion, cotizar
from .entregas import texto_entrega
from .models import Categoria, Color, Producto, Variante


def _productos_activos():
    """Consulta base: productos activos con su categoría y variantes ya cargadas
    (evita hacer una consulta a la base de datos por cada producto)."""
    return Producto.objects.filter(activo=True).select_related("categoria").prefetch_related(
        Prefetch("variantes", queryset=Variante.objects.filter(activa=True).select_related("color"))
    )


SLUG_KITS = "kits"  # categoría que se muestra en su propia sección de la portada

# Grupos de tallas para los filtros de la lista.
GRUPOS_TALLA = {
    "nina": ("Niña", ["2-4", "6-8", "10-12"]),
    "adulto": ("Adulto", ["CH", "M", "G", "EG"]),
}


def inicio(request):
    """Portada: una tarjeta por categoría (con su producto destacado como imagen)
    y la sección de kits navideños."""
    productos = _productos_activos()
    categorias = []
    for cat in Categoria.objects.exclude(slug=SLUG_KITS):
        de_cat = [p for p in productos if p.categoria_id == cat.pk]
        if not de_cat:
            continue
        # Imagen: el destacado de la categoría (o el primero).
        muestra = next((p for p in de_cat if p.destacado), de_cat[0])
        categorias.append({
            "categoria": cat,
            "muestra": muestra,
            "desde": min(p.precio_base for p in de_cat),
        })
    contexto = {
        "categorias": categorias,
        "kits": productos.filter(categoria__slug=SLUG_KITS, destacado=True)[:3],
        "mono_personalizable": productos.filter(personalizable=True).first(),
    }
    return render(request, "catalogo/inicio.html", contexto)


def lista(request, slug=None):
    """Lista de productos. Filtros opcionales en la URL: ?talla=nina|adulto&color=<id>."""
    categoria = None
    productos = _productos_activos()
    if slug:
        categoria = get_object_or_404(Categoria, slug=slug)
        productos = productos.filter(categoria=categoria)

    # Filtros disponibles: solo los que tienen sentido para estos productos.
    variantes = Variante.objects.filter(producto__in=productos, activa=True)
    tallas_usadas = set(variantes.values_list("talla", flat=True))
    filtros_talla = [
        {"clave": clave, "nombre": nombre}
        for clave, (nombre, tallas) in GRUPOS_TALLA.items()
        if tallas_usadas & set(tallas)
    ]
    filtros_color = list(
        Color.objects.filter(pk__in=variantes.values("color")).order_by("orden")
    )
    if len(filtros_color) < 2:   # con un solo color no hace falta filtrar
        filtros_color = []
    if len(filtros_talla) < 2:
        filtros_talla = []

    # Aplicar los filtros elegidos.
    talla_sel = request.GET.get("talla", "")
    if talla_sel in GRUPOS_TALLA:
        productos = productos.filter(
            variantes__talla__in=GRUPOS_TALLA[talla_sel][1], variantes__activa=True
        ).distinct()
    color_sel = request.GET.get("color", "")
    color_sel = int(color_sel) if color_sel.isdigit() else None
    if color_sel:
        productos = productos.filter(variantes__color_id=color_sel, variantes__activa=True).distinct()

    return render(request, "catalogo/lista.html", {
        "categoria": categoria,
        "categoria_actual": slug,
        "productos": productos,
        "filtros_talla": filtros_talla,
        "filtros_color": filtros_color,
        "talla_sel": talla_sel,
        "color_sel": color_sel,
    })


def ayuda(request):
    """Políticas de envío, cambios y devoluciones, y cancelación."""
    return render(request, "catalogo/ayuda.html", {"dias_envio": settings.DIAS_ENVIO})


def _agrupar_colores(colores):
    """Ordena los colores de una parte por grupo (Escolares, Navideños, Básicos)
    para mostrarlos separados en la página."""
    grupos = []
    for clave, nombre in Color.GRUPOS:
        del_grupo = [c for c in colores if c.grupo == clave and c.activo]
        if del_grupo:
            grupos.append({"nombre": nombre, "colores": del_grupo})
    return grupos


def _para_combinar(producto, cuantos=4):
    """'Combínalo con…': un producto destacado de cada una de las otras categorías
    y, si sobra lugar, más kits."""
    otros = list(
        _productos_activos().exclude(categoria=producto.categoria)
        .order_by("categoria__orden", "-destacado", "nombre")
    )
    elegidos, categorias_vistas = [], set()
    for p in otros:                      # 1) uno por categoría
        if p.categoria_id not in categorias_vistas:
            elegidos.append(p)
            categorias_vistas.add(p.categoria_id)
    for p in otros:                      # 2) completar con kits
        if len(elegidos) >= cuantos:
            break
        if p not in elegidos and p.categoria.slug == SLUG_KITS:
            elegidos.append(p)
    return elegidos[:cuantos]


def detalle(request, slug):
    producto = get_object_or_404(_productos_activos(), slug=slug)
    contexto = {
        "producto": producto,
        "categoria_actual": producto.categoria.slug,
        "texto_entrega": texto_entrega(producto.dias_elaboracion),
        "combina": _para_combinar(producto),
    }

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
        # Datos para producto.js: colores y variantes (talla, color, existencias).
        variantes = list(producto.variantes.all())
        contexto["config_variantes"] = {
            "colores": [
                {"id": c.pk, "nombre": c.nombre, "hex": c.codigo_hex, "slug": slugify(c.nombre)}
                for c in producto.colores_disponibles
            ],
            "variantes": [
                {
                    "sku": v.sku,
                    "talla": v.talla,
                    "talla_nombre": v.get_talla_display(),
                    "color": v.color_id,
                    "existencias": v.existencias,
                    "precio_extra": str(v.precio_extra),
                }
                for v in variantes
            ],
        }

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
