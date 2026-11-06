"""
Procesadores de contexto: agregan variables a TODAS las plantillas.
"""
from django.conf import settings

from .models import Categoria, Temporada


def categorias_menu(request):
    """Menú, identidad de la tienda, temporada vigente y versión de los archivos estáticos."""
    return {
        "categorias_menu": Categoria.objects.all(),
        "nombre_tienda": settings.NOMBRE_TIENDA,
        "lema_tienda": settings.LEMA_TIENDA,
        "temporada_vigente": Temporada.actual(),
        "version_estaticos": settings.VERSION_ESTATICOS,
    }
