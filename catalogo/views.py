"""
Vistas: reciben la petición del navegador, consultan los modelos y responden.

inicio       -> portada: temporada vigente, categorías, destacados y "Así de fácil".
lista        -> catálogo completo o por categoría, con filtros por talla y color.
temporada    -> productos de una temporada activa.
ayuda        -> políticas de envío, cambios/devoluciones y cancelación.
privacidad   -> aviso de privacidad.
terminos     -> términos y condiciones de la demo.
robots       -> instrucciones para los buscadores (/robots.txt).
salud        -> revisión del servidor para la plataforma de publicación (/salud/).
detalle      -> página de un producto (simulador si es personalizable).
api_cotizar  -> recibe la selección en JSON y devuelve el precio calculado.
"""
import json

from django.conf import settings
from django.db import connection
from django.db.models import Prefetch
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.templatetags.static import static
from django.views.decorators.http import require_POST

from .cotizacion import TALLAS_CALCETA, ErrorCotizacion, cotizar
from .entregas import texto_entrega
from .models import Categoria, Color, Estampado, Producto, Temporada, Variante


def _productos_activos():
    """Consulta base: productos activos con su categoría y variantes ya cargadas
    (evita hacer una consulta a la base de datos por cada producto)."""
    return Producto.objects.filter(activo=True).select_related("categoria").prefetch_related(
        Prefetch("variantes", queryset=Variante.objects.filter(activa=True).select_related("color"))
    )


SLUG_KITS = "kits"   # categoría de los kits navideños

# Grupos de tallas para los filtros de la lista.
GRUPOS_TALLA = {
    "nina": ("Niña", ["2-4", "6-8", "10-12"]),
    "adulto": ("Adulto", ["CH", "M", "G", "EG"]),
}


def _uno_por_categoria(productos, limite):
    """Escoge productos alternando categorías (uno de cada una, luego otra vuelta...)
    hasta juntar 'limite'. Así la portada muestra variedad y no 6 suéteres seguidos."""
    grupos = {}
    for p in productos:
        grupos.setdefault(p.categoria_id, []).append(p)
    elegidos = []
    while len(elegidos) < limite and any(grupos.values()):
        for lista_cat in grupos.values():
            if lista_cat and len(elegidos) < limite:
                elegidos.append(lista_cat.pop(0))
    return elegidos


def inicio(request):
    """Portada: temporada vigente, una tarjeta por categoría y productos destacados.

    Todo sale de la base de datos: al crear una categoría, un producto o una temporada
    en el admin, la portada se actualiza sin tocar el código.
    """
    from pedidos.models import ConfiguracionTienda  # import local: evita importar pedidos al cargar catalogo

    productos = _productos_activos()
    temporada = Temporada.actual()
    categorias = []
    for cat in Categoria.objects.all():
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

    # "Esta temporada": una probadita de 4, uno por categoría. Primero los que NO son
    # destacados, para que no se repitan con la sección de Destacados de abajo.
    de_temporada = []
    if temporada:
        de_temporada = _uno_por_categoria(
            sorted(productos.filter(temporadas=temporada), key=lambda p: p.destacado), 4)

    contexto = {
        "categorias": categorias,
        "temporada": temporada,
        "de_temporada": de_temporada,
        # Destacados: los que se marcaron en el admin, sin repetir los de arriba. Máximo 4 (un renglón).
        "destacados": productos.filter(destacado=True).exclude(pk__in=[p.pk for p in de_temporada])[:4],
        "envio_gratis_desde": ConfiguracionTienda.cargar().envio_gratis_desde,
    }
    return render(request, "catalogo/inicio.html", contexto)


def _vitrina(de_cat, limite=5):
    """Los primeros productos que se ven de una categoría en el catálogo general.

    - Kits: los completos primero (más caros) y el Mini al final.
    - Categoría con personalizable (Moños): el personalizable primero y luego
      se alternan las colecciones (navideño, uniforme, con decorado...) para que haya variedad.
    - Las demás: en su orden normal.
    """
    if any(p.categoria.slug == SLUG_KITS for p in de_cat):
        return sorted(de_cat, key=lambda p: (-p.precio_base, p.nombre))[:limite]
    personalizables = [p for p in de_cat if p.personalizable]
    if personalizables:
        listos = sorted((p for p in de_cat if not p.personalizable), key=lambda p: (p.creado, p.pk))
        orden = [c for c, _ in Producto.COLECCIONES] + [""]
        por_coleccion = sorted(listos, key=lambda p: orden.index(p.coleccion) if p.coleccion in orden else len(orden))
        return (personalizables[:1] + _uno_por_coleccion(por_coleccion, limite - 1))[:limite]
    return de_cat[:limite]


def _uno_por_coleccion(productos, limite):
    """Como _uno_por_categoria, pero alternando la colección del moño."""
    grupos = {}
    for p in productos:
        grupos.setdefault(p.coleccion, []).append(p)
    elegidos = []
    while len(elegidos) < limite and any(grupos.values()):
        for lista_col in grupos.values():
            if lista_col and len(elegidos) < limite:
                elegidos.append(lista_col.pop(0))
    return elegidos


def catalogo(request):
    """Catálogo general (/catalogo/): un escaparate con un renglón de cada categoría
    y un botón para ver todos los productos de esa categoría."""
    productos = list(_productos_activos().select_related("categoria"))
    grupos = []
    for cat in Categoria.objects.all():
        de_cat = [p for p in productos if p.categoria_id == cat.pk]
        if de_cat:
            grupos.append({"categoria": cat, "productos": _vitrina(de_cat), "total": len(de_cat)})
    return render(request, "catalogo/catalogo.html", {"grupos": grupos})


def lista(request, slug=None):
    """Lista de productos. Filtros opcionales en la URL: ?talla=nina|adulto&color=<id>."""
    if slug is None:
        return catalogo(request)   # sin categoría: el escaparate general
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
    if len(filtros_color) < 2 or slug == SLUG_KITS:   # en kits el color no ayuda a elegir
        filtros_color = []
    if slug == SLUG_KITS:   # los kits completos primero y el Kit Mini al final
        productos = productos.order_by("-precio_base", "nombre")

    # Categorías con un producto personalizable (Moños): arriba va la sección
    # "Diseña el tuyo" con ese producto, y abajo los diseños listos para usar.
    # Aquí no se muestra el filtro de color: el personalizable admite cualquier
    # color y los diseños listos ya traen sus colores en la foto.
    personalizable = (
        productos.filter(personalizable=True, tipo_personalizacion=Producto.MONO).first()
        if categoria else None
    )
    colores_simulador = []
    if personalizable:
        filtros_color = []
        # Los diseños listos salen en el orden en que se dieron de alta
        # (el mismo orden que en cargar_datos_demo.py).
        productos = productos.exclude(pk=personalizable.pk).order_by("creado", "pk")
        # Colores que se pueden elegir en el simulador (para los puntitos y el conteo).
        colores_simulador = list(
            Color.objects.filter(partes__producto=personalizable, activo=True)
            .distinct().order_by("orden")
        )
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
        "personalizable": personalizable,
        "colores_simulador": colores_simulador,
        "secciones": _secciones(productos) if personalizable else [],
    })


def temporada(request, slug):
    """Todos los productos de una temporada activa, agrupados por categoría
    (Moños, Suéteres, Calcetines, Kits...) en el orden de las categorías."""
    coleccion = get_object_or_404(Temporada, slug=slug, activa=True)
    productos = _productos_activos().filter(temporadas=coleccion)
    grupos = []
    for cat in Categoria.objects.all():
        de_cat = [p for p in productos if p.categoria_id == cat.pk]
        if de_cat:
            grupos.append({"categoria": cat, "productos": de_cat})
    return render(request, "catalogo/temporada.html", {
        "coleccion": coleccion,
        "productos": productos,
        "grupos": grupos,
    })


# Texto y emoji de cada sección de la página de Moños.
SECCIONES = {
    Producto.NAVIDENO: ("🎄", "Navideños.", "Para regalar y lucir en las posadas."),
    Producto.UNIFORME: ("🎒", "Uniforme escolar.", "Los colores de cada escuela, listos para enviar."),
    Producto.DECORADO: ("🎀", "Con decorado.", "Listones estampados, ya combinados."),
    "": ("✨", "Más moños.", "Listos para enviar."),
}


def _secciones(productos):
    """Agrupa los moños listos por colección, en el orden de Producto.COLECCIONES
    (Navideños, Uniforme escolar, Con decorado). Solo incluye secciones con productos."""
    secciones = []
    for clave in [c for c, _ in Producto.COLECCIONES] + [""]:
        de_seccion = [p for p in productos if p.coleccion == clave]
        if de_seccion:
            emoji, titulo, subtitulo = SECCIONES[clave]
            secciones.append({
                "id": clave or "otros", "emoji": emoji, "titulo": titulo,
                "nombre": titulo.rstrip("."), "subtitulo": subtitulo, "productos": de_seccion,
            })
    return secciones


def ayuda(request):
    """Políticas de envío, cambios y devoluciones, y cancelación."""
    return render(request, "catalogo/ayuda.html", {"dias_envio": settings.DIAS_ENVIO})


def privacidad(request):
    return render(request, "catalogo/privacidad.html")


def terminos(request):
    return render(request, "catalogo/terminos.html")


def robots(request):
    """Las páginas privadas no deben aparecer en los buscadores."""
    lineas = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /carrito/",
        "Disallow: /compra/",
        "Disallow: /cuentas/",
        "Disallow: /pedidos/",
        "Disallow: /pagos/",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lineas) + "\n", content_type="text/plain")


def salud(request):
    """Responde 200 si el servidor y la base de datos funcionan."""
    connection.ensure_connection()
    return JsonResponse({"ok": True})


def _datos_estructurados(request, producto):
    """Ficha schema.org del producto para que los buscadores muestren precio y disponibilidad."""
    imagen = producto.imagen.url if producto.imagen else producto.url_imagen_estatica
    datos = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": producto.nombre,
        "description": producto.descripcion,
        "category": producto.categoria.nombre,
        "offers": {
            "@type": "Offer",
            "url": request.build_absolute_uri(producto.get_absolute_url()),
            "priceCurrency": "MXN",
            "price": str(producto.precio_base),
            "availability": "https://schema.org/InStock" if producto.disponible
            else "https://schema.org/OutOfStock",
        },
    }
    if imagen:
        datos["image"] = request.build_absolute_uri(imagen)
    # Se escapan <, > y & para que el texto no pueda cerrar la etiqueta <script>.
    texto = json.dumps(datos, ensure_ascii=False)
    return mark_safe(texto.replace("<", "\\u003C").replace(">", "\\u003E").replace("&", "\\u0026"))


def _agrupar_colores(colores):
    """Ordena los colores de una parte por grupo (Escolares, Navideños, Básicos)
    para mostrarlos separados en la página."""
    grupos = []
    for clave, nombre in Color.GRUPOS:
        del_grupo = [c for c in colores if c.grupo == clave and c.activo]
        if del_grupo:
            grupos.append({"nombre": nombre, "colores": del_grupo})
    return grupos


def _agrupar_estampados(estampados):
    """Estampados agrupados para la página: grupo (Escolares, Navideños, Otros) ->
    diseño (Mariposas, Lunares...) -> sus variantes de color, en el orden del admin.

    Devuelve [{"nombre": "Escolares", "disenos": [{"nombre", "slug", "variantes"}, ...]}, ...]
    """
    grupos = []
    for clave, nombre in Estampado.GRUPOS:
        disenos = {}   # nombre del diseño -> lista de variantes (conserva el orden)
        for e in estampados:
            if e.grupo == clave:
                disenos.setdefault(e.nombre_diseno, []).append(e)
        if disenos:
            grupos.append({
                "nombre": nombre,
                "disenos": [
                    {"nombre": n, "slug": slugify(n), "variantes": v} for n, v in disenos.items()
                ],
            })
    return grupos


def _para_combinar(producto, cuantos=4):
    """'Combínalo con…': un producto destacado de cada una de las otras categorías
    y, si sobra lugar, más productos."""
    otros = list(
        _productos_activos().exclude(categoria=producto.categoria)
        .order_by("categoria__orden", "-destacado", "nombre")
    )
    elegidos, categorias_vistas = [], set()
    for p in otros:                      # 1) uno por categoría
        if p.categoria_id not in categorias_vistas:
            elegidos.append(p)
            categorias_vistas.add(p.categoria_id)
    for p in otros:                      # 2) completar con otros productos
        if len(elegidos) >= cuantos:
            break
        if p not in elegidos:
            elegidos.append(p)
    return elegidos[:cuantos]


def detalle(request, slug):
    producto = get_object_or_404(_productos_activos(), slug=slug)
    contexto = {
        "producto": producto,
        "categoria_actual": producto.categoria.slug,
        "texto_entrega": texto_entrega(producto.dias_elaboracion),
        "combina": _para_combinar(producto),
        "datos_estructurados": _datos_estructurados(request, producto),
    }

    if producto.es_calceta:
        # Personalizador de calcetas: colores por parte, diseños, posición, tamaño y talla.
        partes = list(producto.partes.prefetch_related("colores").select_related("color_inicial"))
        disenos = list(producto.disenos_calceta.filter(activo=True))
        contexto["partes_calceta"] = [
            {"parte": p, "grupos": _agrupar_colores(list(p.colores.all()))} for p in partes
        ]
        contexto["disenos_calceta"] = disenos
        contexto["tallas_calceta"] = [(t, dict(Variante.TALLAS)[t]) for t in TALLAS_CALCETA]
        # Configuración que lee calceta.js desde la página.
        contexto["config_calceta"] = {
            "partes": [p.clave for p in partes],
            "disenos": {d.clave: d.url_imagen for d in disenos},
            # Capas sacadas de una foto real (static() da la URL correcta también en producción).
            "capas": {
                nombre: static(f"simulador/calceta/{nombre}.png")
                for nombre in ("sombra", "cuerpo", "detalles")
            },
        }
    elif producto.personalizable:
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
        contexto["grupos_estampados"] = _agrupar_estampados(estampados)
        # Precio que se muestra junto a "Estampado": el más bajo (hoy todos cuestan igual).
        contexto["precio_estampado"] = min((e.precio_extra for e in estampados), default=0)
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
        # Kits: sus piezas, para la caja "Incluye" (suéter, calcetines, moño).
        contexto["piezas_kit"] = list(producto.piezas.select_related("producto__categoria"))
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
