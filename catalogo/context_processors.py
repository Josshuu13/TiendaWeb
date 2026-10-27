from .models import Categoria


def categorias_menu(request):
    """Categorías para el menú de navegación en todas las páginas."""
    return {"categorias_menu": Categoria.objects.all()}
