from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from catalogo.sitemaps import SITEMAPS

urlpatterns = [
    path("admin/", admin.site.urls),
    path("carrito/", include("carrito.urls")),
    path("cuentas/", include("cuentas.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    path("", include("pedidos.urls")),
    path("", include("catalogo.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
