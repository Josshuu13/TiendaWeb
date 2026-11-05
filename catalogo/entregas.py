"""
Cálculo de la fecha estimada de entrega.

Regla del negocio:
  fecha de entrega = hoy + días de elaboración + días de envío
  Solo se cuentan días hábiles (lunes a viernes).
  Se muestra un rango: del día calculado a dos días hábiles después,
  para dar margen al envío.

En un pedido con varios productos manda el más tardado (se usará en el carrito).
"""
import datetime

from django.conf import settings
from django.utils import timezone

DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MARGEN_DIAS = 2  # días hábiles de margen para el rango


def sumar_dias_habiles(fecha: datetime.date, dias: int) -> datetime.date:
    """Avanza `dias` días hábiles a partir de `fecha` (se saltan sábados y domingos)."""
    while dias > 0:
        fecha += datetime.timedelta(days=1)
        if fecha.weekday() < 5:  # 0 = lunes ... 4 = viernes
            dias -= 1
    return fecha


def rango_entrega(dias_elaboracion: int, hoy: datetime.date | None = None):
    """Devuelve (fecha_mínima, fecha_máxima) de entrega para un producto."""
    hoy = hoy or timezone.localdate()
    minima = sumar_dias_habiles(hoy, dias_elaboracion + settings.DIAS_ENVIO)
    maxima = sumar_dias_habiles(minima, MARGEN_DIAS)
    return minima, maxima


def fecha_legible(fecha: datetime.date) -> str:
    """'lunes 9 de noviembre'."""
    return f"{DIAS_SEMANA[fecha.weekday()]} {fecha.day} de {MESES[fecha.month - 1]}"


def texto_entrega(dias_elaboracion: int, hoy: datetime.date | None = None) -> str:
    """Texto para la página: 'Si pides hoy, llega entre el lunes 9 y el miércoles 11 de noviembre.'"""
    minima, maxima = rango_entrega(dias_elaboracion, hoy)
    inicio = f"{DIAS_SEMANA[minima.weekday()]} {minima.day}"
    if minima.month != maxima.month:
        inicio = fecha_legible(minima)
    return f"Si pides hoy, llega entre el {inicio} y el {fecha_legible(maxima)}."
