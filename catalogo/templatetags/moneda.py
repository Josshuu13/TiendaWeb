"""Filtros para mostrar importes y teléfonos siempre igual: $1,234.50 y 55 1234 5678."""
from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def pesos(valor):
    try:
        return f"${Decimal(valor):,.2f}"
    except (InvalidOperation, TypeError, ValueError):
        return ""


@register.filter
def telefono(numero):
    numero = str(numero)
    return f"{numero[:2]} {numero[2:6]} {numero[6:]}" if len(numero) == 10 else numero
