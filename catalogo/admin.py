"""
Panel de administración (/admin/).

Aquí se configura qué ve el equipo de la tienda: listas, filtros y campos editables.
Django genera los formularios a partir de los modelos.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Categoria, Color, Combinacion, CombinacionParte, Estampado, Parte, Producto, Variante,
)

# Textos del encabezado del panel.
admin.site.site_header = "Moñería – Administración"
admin.site.site_title = "Moñería"
admin.site.index_title = "Panel de la tienda"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "orden"]
    list_editable = ["orden"]
    prepopulated_fields = {"slug": ["nombre"]}  # el slug se llena solo desde el nombre


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ["muestra", "nombre", "codigo_hex", "grupo", "activo", "orden"]
    list_display_links = ["nombre"]
    list_editable = ["grupo", "activo", "orden"]
    list_filter = ["grupo", "activo"]
    search_fields = ["nombre"]

    @admin.display(description="")
    def muestra(self, obj):
        """Circulito con el color real, para identificarlo rápido en la lista."""
        return format_html(
            '<span style="display:inline-block;width:22px;height:22px;'
            'border-radius:50%;border:1px solid #999;background:{}"></span>',
            obj.codigo_hex,
        )


class VarianteInline(admin.TabularInline):
    """Tabla de variantes (tallas y existencias) dentro del formulario del producto."""

    model = Variante
    extra = 1
    fields = ["talla", "color", "sku", "existencias", "precio_extra", "activa"]


class ParteInline(admin.StackedInline):
    """Partes del moño (capas) dentro del formulario del producto personalizable."""

    model = Parte
    extra = 0
    filter_horizontal = ["colores"]  # selector cómodo para elegir colores permitidos


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        "nombre", "categoria", "precio_base", "dias_elaboracion",
        "personalizable", "existencias", "activo", "destacado",
    ]
    list_filter = ["categoria", "personalizable", "activo"]
    list_editable = ["precio_base", "activo", "destacado"]
    search_fields = ["nombre", "descripcion"]
    prepopulated_fields = {"slug": ["nombre"]}

    def get_inlines(self, request, obj):
        """Personalizable -> muestra sus Partes. De catálogo -> muestra sus Variantes."""
        if obj and obj.personalizable:
            return [ParteInline]
        return [VarianteInline]

    @admin.display(description="Existencias")
    def existencias(self, obj):
        return "Sobre pedido" if obj.personalizable else obj.existencias_totales


@admin.register(Variante)
class VarianteAdmin(admin.ModelAdmin):
    list_display = ["__str__", "sku", "existencias", "precio_extra", "activa"]
    list_filter = ["producto__categoria", "talla", "activa"]
    list_editable = ["existencias", "activa"]
    search_fields = ["sku", "producto__nombre"]


@admin.register(Estampado)
class EstampadoAdmin(admin.ModelAdmin):
    list_display = ["vista", "nombre", "precio_extra", "activo", "orden"]
    list_display_links = ["nombre"]
    list_editable = ["precio_extra", "activo", "orden"]
    prepopulated_fields = {"clave": ["nombre"]}
    filter_horizontal = ["productos"]

    @admin.display(description="")
    def vista(self, obj):
        """Miniatura de la tira del listón estampado."""
        return format_html(
            '<img src="{}" style="height:48px;width:24px;object-fit:cover;'
            'border:1px solid #ccc;border-radius:3px">',
            obj.url_imagen,
        )


class CombinacionParteInline(admin.TabularInline):
    """Un renglón por parte del moño con el color que lleva en la combinación."""

    model = CombinacionParte
    extra = 0


@admin.register(Combinacion)
class CombinacionAdmin(admin.ModelAdmin):
    list_display = ["nombre", "producto", "estampado", "activa", "orden"]
    list_editable = ["activa", "orden"]
    inlines = [CombinacionParteInline]
