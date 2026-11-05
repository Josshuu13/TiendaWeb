"""
Procesadores de contexto: agregan variables a TODAS las plantillas.
"""
from django.conf import settings

from .models import Categoria


def categorias_menu(request):
    """Categorías para el menú de navegación y versión de los archivos estáticos."""
    return {
        "categorias_menu": Categoria.objects.all(),
        "version_estaticos": settings.VERSION_ESTATICOS,
    }
