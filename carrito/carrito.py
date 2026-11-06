"""
Carrito de compras guardado en la sesión del navegador.

Solo guarda la selección del cliente (identificadores y cantidad), con el mismo
formato que usa la cotización. NUNCA guarda precios: cada vez que se muestra, se
vuelve a pasar por catalogo.cotizacion.cotizar(), que valida y calcula el importe.
Así, si cambia un precio o se agota una talla, el carrito lo refleja al instante.
"""
import base64
import binascii
import io
import json
import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from PIL import Image, UnidentifiedImageError

from catalogo.cotizacion import Cotizacion, ErrorCotizacion, cotizar
from catalogo.entregas import texto_entrega

CLAVE_SESION = "carrito"
TAMANO_MAXIMO_VISTA = 200_000  # caracteres de la vista previa del moño
PATRON_VISTA = re.compile(r"^data:image/(webp|png);base64,([A-Za-z0-9+/=]+)$")


def vista_valida(vista) -> str:
    """Devuelve la vista previa del moño si es una imagen real, o "" si no lo es.

    La imagen la genera el navegador, así que no se confía en ella: se revisa que sea
    una imagen pequeña. Es solo una referencia visual; lo que manda son las opciones.
    """
    if not isinstance(vista, str) or len(vista) > TAMANO_MAXIMO_VISTA:
        return ""
    coincide = PATRON_VISTA.match(vista)
    if not coincide:
        return ""
    try:
        Image.open(io.BytesIO(base64.b64decode(coincide.group(2)))).verify()
    except (binascii.Error, UnidentifiedImageError, OSError, ValueError):
        return ""
    return vista


def _limpiar(datos) -> dict:
    """Se queda solo con los campos del formato de selección; lo demás se ignora."""
    if not isinstance(datos, dict):
        raise ErrorCotizacion("Formato de selección no válido.")
    seleccion = {"producto": datos.get("producto"), "cantidad": datos.get("cantidad", 1)}
    for campo in ("variante", "opciones"):
        if datos.get(campo):
            seleccion[campo] = datos[campo]
    return seleccion


def _huella(seleccion: dict) -> str:
    """Identifica una selección sin importar la cantidad, para juntar repetidos."""
    sin_cantidad = {k: v for k, v in seleccion.items() if k != "cantidad"}
    return json.dumps(sin_cantidad, sort_keys=True)


@dataclass
class LineaCarrito:
    """Un renglón del carrito ya validado por el servidor."""

    id: str
    seleccion: dict
    vista: str = ""
    cotizacion: Cotizacion | None = None
    error: str = ""

    @property
    def cantidad(self) -> int:
        return int(self.seleccion.get("cantidad", 1))


@dataclass
class Resumen:
    """Totales del carrito que se muestran y con los que se crea el pedido."""

    lineas: list = field(default_factory=list)
    costo_envio: Decimal = Decimal("0")

    @property
    def validas(self) -> list:
        return [linea for linea in self.lineas if linea.cotizacion]

    @property
    def tiene_errores(self) -> bool:
        return any(linea.error for linea in self.lineas)

    @property
    def subtotal(self) -> Decimal:
        return sum((linea.cotizacion.total for linea in self.validas), Decimal("0"))

    @property
    def envio(self) -> Decimal:
        return self.costo_envio if self.validas else Decimal("0")

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.envio

    @property
    def piezas(self) -> int:
        return sum(linea.cantidad for linea in self.validas)

    @property
    def dias_elaboracion(self) -> int:
        """En un pedido mixto manda el producto más tardado."""
        return max((linea.cotizacion.dias_elaboracion for linea in self.validas), default=0)

    @property
    def texto_entrega(self) -> str:
        return texto_entrega(self.dias_elaboracion)


class Carrito:
    def __init__(self, session):
        self.session = session
        self.lineas = session.get(CLAVE_SESION, [])

    def _guardar(self):
        self.session[CLAVE_SESION] = self.lineas
        self.session.modified = True

    def _buscar(self, linea_id):
        return next((linea for linea in self.lineas if linea["id"] == linea_id), None)

    @property
    def piezas(self) -> int:
        return sum(int(linea["seleccion"].get("cantidad", 1)) for linea in self.lineas)

    def agregar(self, datos) -> None:
        """Agrega una selección. Si ya estaba, suma la cantidad."""
        seleccion = _limpiar(datos)
        huella = _huella(seleccion)
        existente = next((linea for linea in self.lineas if _huella(linea["seleccion"]) == huella), None)
        cot = cotizar(seleccion)  # lanza ErrorCotizacion si no es válida
        if existente:
            seleccion["cantidad"] = int(existente["seleccion"]["cantidad"]) + cot.cantidad
            cot = cotizar(seleccion)  # la suma también debe caber en existencias
        seleccion["cantidad"] = cot.cantidad

        if existente:
            existente["seleccion"] = seleccion
        else:
            self.lineas.append({
                "id": uuid.uuid4().hex,
                "seleccion": seleccion,
                "vista": vista_valida(datos.get("vista")),
            })
        self._guardar()

    def cambiar_cantidad(self, linea_id, cantidad) -> None:
        linea = self._buscar(linea_id)
        if linea is None:
            raise ErrorCotizacion("Ese producto ya no está en tu carrito.")
        seleccion = {**linea["seleccion"], "cantidad": cantidad}
        seleccion["cantidad"] = cotizar(seleccion).cantidad
        linea["seleccion"] = seleccion
        self._guardar()

    def quitar(self, linea_id) -> None:
        self.lineas = [linea for linea in self.lineas if linea["id"] != linea_id]
        self._guardar()

    def vaciar(self) -> None:
        self.lineas = []
        self._guardar()

    def resumen(self, costo_envio=Decimal("0")) -> Resumen:
        """Vuelve a cotizar cada renglón con los precios y existencias actuales."""
        lineas = []
        for datos in self.lineas:
            linea = LineaCarrito(id=datos["id"], seleccion=datos["seleccion"], vista=datos.get("vista", ""))
            try:
                linea.cotizacion = cotizar(linea.seleccion)
            except ErrorCotizacion as e:
                linea.error = str(e)
            lineas.append(linea)
        return Resumen(lineas=lineas, costo_envio=costo_envio)
