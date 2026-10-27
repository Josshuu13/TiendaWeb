from django.contrib import admin
from django.utils.html import format_html

from .models import Categoria, Color, Decoracion, Parte, Producto, Variante

admin.site.site_header = "Moñería – Administración"
admin.site.site_title = "Moñería"
admin.site.index_title = "Panel de la tienda"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "orden"]
    list_editable = ["orden"]
    prepopulated_fields = {"slug": ["nombre"]}


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ["muestra", "nombre", "codigo_hex", "activo", "orden"]
    list_display_links = ["nombre"]
    list_editable = ["activo", "orden"]
    search_fields = ["nombre"]

    @admin.display(description="")
    def muestra(self, obj):
        return format_html(
            '<span style="display:inline-block;width:22px;height:22px;'
            'border-radius:50%;border:1px solid #999;background:{}"></span>',
            obj.codigo_hex,
        )


class VarianteInline(admin.TabularInline):
    model = Variante
    extra = 1
    fields = ["talla", "color", "sku", "existencias", "precio_extra", "activa"]


class ParteInline(admin.StackedInline):
    model = Parte
    extra = 0
    filter_horizontal = ["colores"]


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


@admin.register(Decoracion)
class DecoracionAdmin(admin.ModelAdmin):
    list_display = ["nombre", "precio_extra", "dias_extra", "activa"]
    list_editable = ["precio_extra", "activa"]
    prepopulated_fields = {"clave": ["nombre"]}
    filter_horizontal = ["productos"]
