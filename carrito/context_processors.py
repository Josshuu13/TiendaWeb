from .carrito import Carrito


def carrito(request):
    """Número de piezas para el contador de la barra superior."""
    return {"carrito_piezas": Carrito(request.session).piezas}
