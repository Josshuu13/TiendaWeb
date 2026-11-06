"""Mapa del sitio (/sitemap.xml): le dice a los buscadores qué páginas existen."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Categoria, Producto, Temporada


class ProductoSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Producto.objects.filter(activo=True)

    def lastmod(self, producto):
        return producto.creado


class CategoriaSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Categoria.objects.all()


class TemporadaSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Temporada.objects.filter(activa=True)


class PaginasSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.4

    def items(self):
        return ["catalogo:inicio", "catalogo:lista", "catalogo:ayuda"]

    def location(self, nombre):
        return reverse(nombre)


SITEMAPS = {
    "productos": ProductoSitemap, "categorias": CategoriaSitemap,
    "temporadas": TemporadaSitemap, "paginas": PaginasSitemap,
}
