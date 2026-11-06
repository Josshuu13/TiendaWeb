from .models import ConfiguracionTienda


def tienda(request):
    """Datos de soporte disponibles en todas las páginas."""
    return {"tienda": ConfiguracionTienda.cargar()}
