"""
Cotización validada en el servidor (lógica de negocio).

El navegador (catálogo o simulador) solo manda QUÉ eligió el cliente, nunca el
precio. Aquí se busca todo en la base de datos, se valida y se calcula el importe.

Formato de entrada (el mismo que se mandará al carrito):

  Producto de catálogo:
    {"producto": "sueter-reno", "variante": "SUE-RENO-M", "cantidad": 2}

  Moño personalizable (colores por id; estampado por clave, opcional):
    {"producto": "mono-clasico",
     "opciones": {"patas": 3, "baseabajo": 5, "basearriba": 3,
                  "decorado": 7, "tiras": 1, "nudo": 3,
                  "estampado": "tejido-rojo"},
     "cantidad": 1}

  Si se elige un estampado, la parte que lo admite (el decorado) ya no necesita
  color, porque se muestra con los colores reales del listón estampado.
"""
from dataclasses import dataclass, field
from decimal import Decimal

from .models import Color, Producto

CANTIDAD_MAXIMA = 50  # límite por línea, para evitar errores de captura


class ErrorCotizacion(ValueError):
    """La selección no es válida (producto inexistente, color no permitido, etc.)."""


@dataclass
class Concepto:
    """Una línea del desglose: por ejemplo 'Decorado estampado: Tejido rojo – $25'."""

    descripcion: str
    importe: Decimal


@dataclass
class Cotizacion:
    """Resultado de cotizar: desglose por pieza, cantidad y datos para el pedido."""

    producto: Producto
    cantidad: int
    conceptos: list = field(default_factory=list)  # desglose por pieza
    dias_elaboracion: int = 0
    variante: object = None
    seleccion: dict = field(default_factory=dict)  # configuración legible para el pedido

    @property
    def precio_unitario(self) -> Decimal:
        return sum((c.importe for c in self.conceptos), Decimal("0"))

    @property
    def total(self) -> Decimal:
        return self.precio_unitario * self.cantidad

    def como_dict(self) -> dict:
        """Versión lista para mandar como JSON al navegador."""
        return {
            "producto": self.producto.slug,
            "nombre": self.producto.nombre,
            "cantidad": self.cantidad,
            "conceptos": [
                {"descripcion": c.descripcion, "importe": str(c.importe)}
                for c in self.conceptos
            ],
            "precio_unitario": str(self.precio_unitario),
            "total": str(self.total),
            "dias_elaboracion": self.dias_elaboracion,
            "seleccion": self.seleccion,
        }


def _leer_cantidad(valor) -> int:
    """Convierte la cantidad a entero y revisa que esté en el rango permitido."""
    try:
        cantidad = int(valor)
    except (TypeError, ValueError):
        raise ErrorCotizacion("La cantidad debe ser un número entero.")
    if not 1 <= cantidad <= CANTIDAD_MAXIMA:
        raise ErrorCotizacion(f"La cantidad debe estar entre 1 y {CANTIDAD_MAXIMA}.")
    return cantidad


def cotizar(datos: dict) -> Cotizacion:
    """Punto de entrada: decide si es producto de catálogo o personalizable."""
    if not isinstance(datos, dict):
        raise ErrorCotizacion("Formato de cotización no válido.")

    try:
        producto = Producto.objects.get(slug=datos.get("producto"), activo=True)
    except Producto.DoesNotExist:
        raise ErrorCotizacion("El producto no existe o no está disponible.")

    cantidad = _leer_cantidad(datos.get("cantidad", 1))

    if producto.personalizable:
        return _cotizar_personalizable(producto, datos.get("opciones") or {}, cantidad)
    return _cotizar_catalogo(producto, datos.get("variante"), cantidad)


def _cotizar_catalogo(producto, sku, cantidad) -> Cotizacion:
    """Suéteres, calcetines y moño escolar: se valida la variante y sus existencias."""
    variante = producto.variantes.filter(sku=sku, activa=True).select_related("color").first()
    if variante is None:
        raise ErrorCotizacion("Elige una talla o color disponible.")
    if variante.existencias < cantidad:
        if variante.existencias == 0:
            raise ErrorCotizacion("Esta variante está agotada.")
        raise ErrorCotizacion(f"Solo quedan {variante.existencias} piezas de esta variante.")

    cot = Cotizacion(
        producto=producto,
        cantidad=cantidad,
        variante=variante,
        dias_elaboracion=producto.dias_elaboracion,
    )
    cot.conceptos.append(Concepto(f"{producto.nombre} (precio base)", producto.precio_base))
    if variante.precio_extra:
        cot.conceptos.append(
            Concepto(f"Talla {variante.get_talla_display()}", variante.precio_extra)
        )
    cot.seleccion = {"talla": variante.get_talla_display()}
    if variante.color:
        cot.seleccion["color"] = variante.color.nombre
    return cot


def _cotizar_personalizable(producto, opciones, cantidad) -> Cotizacion:
    """Moño del simulador: valida el color de cada parte y el estampado opcional."""
    if not isinstance(opciones, dict):
        raise ErrorCotizacion("Las opciones del moño no son válidas.")

    cot = Cotizacion(
        producto=producto,
        cantidad=cantidad,
        dias_elaboracion=producto.dias_elaboracion,
    )
    cot.conceptos.append(Concepto(f"{producto.nombre} (precio base)", producto.precio_base))

    # 1) Estampado (opcional). Se valida primero porque cambia lo que se exige al decorado.
    estampado = None
    clave_estampado = opciones.get("estampado")
    if clave_estampado:
        estampado = producto.estampados.filter(clave=clave_estampado, activo=True).first()
        if estampado is None:
            raise ErrorCotizacion("El estampado elegido no está disponible.")

    # 2) Color de cada parte. Solo se aceptan claves que existan en este moño.
    claves_validas = {"estampado"}
    for parte in producto.partes.prefetch_related("colores"):
        claves_validas.add(parte.clave)

        # Si hay estampado, la parte que lo admite se muestra estampada (sin color).
        if estampado and parte.admite_estampado:
            cot.seleccion[parte.nombre] = f"Estampado: {estampado.nombre}"
            continue

        color_id = opciones.get(parte.clave)
        if color_id in (None, ""):
            raise ErrorCotizacion(f"Elige un color para {parte.nombre.lower()}.")
        try:
            color = parte.colores.get(pk=int(color_id), activo=True)
        except (ValueError, TypeError, Color.DoesNotExist):
            raise ErrorCotizacion(
                f"El color elegido no está disponible para {parte.nombre.lower()}."
            )
        cot.seleccion[parte.nombre] = color.nombre

    # 3) Cualquier opción inventada (por ejemplo "precio") se rechaza.
    desconocidas = set(opciones) - claves_validas
    if desconocidas:
        raise ErrorCotizacion(f"Opciones no reconocidas: {', '.join(sorted(desconocidas))}.")

    # 4) Costo extra del estampado.
    if estampado and estampado.precio_extra:
        cot.conceptos.append(
            Concepto(f"Decorado estampado: {estampado.nombre}", estampado.precio_extra)
        )

    return cot
