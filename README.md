# Pretexto – Tienda en línea de productos de temporada

Proyecto de **Negocios Electrónicos y Desarrollo Web** (Facultad de Ingeniería, UNAM).
Tienda B2C pensada para vender lo que haya en cada temporada. La primera colección son moños
para niña con simulador visual, suéteres y calcetines navideños, y los productos, categorías y
temporadas se administran desde el panel, sin programar.

Es una demostración académica: los pagos son de prueba y no se realizan ventas reales.

## Qué incluye

- **Temporadas** que se programan en el admin: aviso, portada, productos y fechas.
- **Catálogo** por categorías con filtros por talla y color.
- **Simulador visual del moño** con fotos reales: 6 partes con color propio y decorado liso o estampado.
- **Personalizador paso a paso** con "Lo más vendido", zoom y Restablecer.
- **Cinco suéteres navideños** en tallas de niña y adulto, sin personalización.
- **Cotización validada en el servidor**: el navegador solo manda la selección.
- **Carrito mixto** con cantidades y actualización sin recargar la página.
- **Cuentas** con registro, inicio de sesión y recuperación de contraseña.
- **Compra** con dirección, envío de tarifa fija y fecha estimada de entrega.
- **Pago con Stripe** en modo de pruebas, confirmado por webhook firmado.
- **Mis pedidos** con ID de pedido, línea de tiempo, transportista, guía y teléfonos.
- **Soporte técnico** por WhatsApp con el ID del pedido, y teléfono siempre visible.
- **Cancelaciones y devoluciones** por solicitud, resueltas desde el admin.
- **Panel de administración** en español (`/admin/`).
- **Correos automáticos** al cambiar el estado del pedido.
- 170 pruebas automáticas con pytest.

La arquitectura, los diagramas y las decisiones técnicas están en [docs/arquitectura.md](docs/arquitectura.md).

## Cómo correrlo (Windows, macOS o Linux)

Requiere Python 3.12 o superior. En macOS usa `python3` para crear el entorno; una vez activado,
`python` ya funciona.

```bash
# 1. Crear y activar el entorno virtual
python3 -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements-dev.txt

# 3. Crear la base de datos y cargar el catálogo de ejemplo
python manage.py migrate
python manage.py cargar_datos_demo

# 4. Crear un usuario para el panel de administración
python manage.py createsuperuser

# 5. Levantar el servidor
python manage.py runserver
```

- Tienda: http://127.0.0.1:8000/
- Administración: http://127.0.0.1:8000/admin/

No hace falta configurar nada: sin llaves de Stripe se usa un pago simulado y los correos se imprimen
en la terminal. Para usar Stripe, copia `.env.example` como `.env` y sigue [docs/publicacion.md](docs/publicacion.md).

## Pruebas y calidad

```bash
pytest
ruff check .
```

GitHub Actions ejecuta esto en cada Pull Request, sobre PostgreSQL. La forma de trabajar en equipo está
en [CONTRIBUTING.md](CONTRIBUTING.md).

## Estructura

```
tiendaWeb/          configuración, URLs y encabezados de seguridad
catalogo/           productos, simulador, cotización y fechas de entrega
  cotizacion.py     cálculo y validación de precios
  entregas.py       fecha estimada de entrega
carrito/
  carrito.py        carrito en la sesión; siempre recotiza
pedidos/
  models.py         pedido, historial, pagos, solicitudes y configuración
  servicios.py      reglas de negocio: crear, pagar, avanzar, cancelar
  pagos.py          conexión con Stripe
  notificaciones.py correos automáticos
cuentas/            registro e inicio de sesión
templates/          HTML por sección
static/css          sistema de diseño propio
static/js           cotizador.js, simulador.js, personalizador.js, producto.js y cantidad.js
static/simulador/   capas del moño (PNG en gris), mapa del decorado y tiras de estampados
static/img/sueteres imágenes de los suéteres (generadas con IA)
static/vendor       htmx
docs/               arquitectura, manual, publicación y bitácora
```

## Formato de la selección (catálogo → cotización → carrito)

El cliente **nunca** manda precios; solo identificadores.

```json
{ "producto": "sueter-reno", "variante": "SUETER-RENO-M-ROJNAV", "cantidad": 2 }

{ "producto": "mono-clasico",
  "opciones": { "patas": 11, "baseabajo": 1, "basearriba": 11,
                "decorado": 12, "tiras": 1, "nudo": 11,
                "estampado": "tejido-rojo" },
  "cantidad": 1 }
```

En el moño, cada parte lleva el **id** del color. `estampado` es opcional y lleva la **clave** del listón estampado; si se manda, el decorado se muestra estampado y su color no se usa.

## Cómo funciona el simulador

1. Cada parte del moño es un PNG **en escala de grises** con fondo transparente (`static/simulador/mono-clasico/`). Todas miden lo mismo y encajan una sobre otra.
2. `simulador.js` dibuja las capas en orden (de atrás hacia adelante) en un `<canvas>` y tiñe cada una con el color elegido usando la fusión **multiply**: lo claro queda del color puro y las sombras del mismo color, más oscuro. Así se conservan la textura y el volumen del listón.
3. Para un **estampado**, se usa la foto del listón recta (`static/simulador/estampados/`) y un mapa (`decorado-uv.png`) que indica en qué parte del ancho del listón cae cada píxel del decorado; encima se aplican las sombras de la foto original.
4. `cotizador.js` avisa los cambios con el evento `seleccion-cambiada`; el simulador solo escucha ese evento y no sabe nada de precios.

### Personalizador paso a paso

El cliente elige las partes en orden (campo `paso` de cada Parte): Patas → Base superior → Base inferior → Decorado → Tiras → Nudo, con botones Anterior/Siguiente. Al cambiar de paso, la parte se resalta en el moño. **Restablecer** vuelve a los colores iniciales y **Lo más vendido** aplica combinaciones listas.

### Agregar una combinación a "Lo más vendido" (sin programar)

En el admin: **Combinaciones (lo más vendido) → Añadir**. Ponle nombre, elige el producto y agrega un renglón por parte con su color (opcionalmente un estampado para el decorado).

### Agregar un listón estampado nuevo (sin programar)

1. Toma una foto del listón **recto, vertical y de frente**, con luz pareja.
2. Recórtala **justo al ancho del listón** (sin mesa ni fondo).
3. En el admin: **Estampados → Añadir**, sube la imagen, ponle nombre, precio extra y marca el producto "Moño clásico personalizable".

### Cambiar las fotos de las capas

En el admin, dentro del producto, cada **Parte** tiene el campo *Imagen capa*. Si se sube una imagen ahí, se usa en lugar de la de `static/simulador/`. Debe medir lo mismo que las demás capas.

## Producción

La tienda se publica en Render con PostgreSQL. Los pasos están en [docs/publicacion.md](docs/publicacion.md).

## Equipo

- Santiago González Kevin
- Cardoso Martínez Josue
- Flores Herrera Oswaldo
