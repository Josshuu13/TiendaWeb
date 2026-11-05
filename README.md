# Moñería – Tienda web de moños personalizables

Proyecto de **Negocios Electrónicos y Desarrollo Web** (Facultad de Ingeniería, UNAM).
Tienda B2C de moños para niña con simulador visual, más suéteres y calcetines navideños.

## Qué hay hasta ahora

- Proyecto Django `tiendaWeb` con la app `catalogo`.
- Modelos: `Categoria`, `Color` (agrupados en escolares, navideños y básicos), `Producto`, `Variante` (talla, color y existencias), `Parte` (capas del moño) y `Estampado` (listones decorados).
- **Simulador visual del moño** con fotos reales: 6 partes con color propio (patas, base de abajo, base de arriba, decorado, tiras y nudo) y decorado liso o estampado.
- Panel de administración en español (`/admin/`).
- Páginas: inicio, catálogo por categoría y detalle de producto.
- **Cotización validada en el servidor** (`/api/cotizar/`): el navegador solo manda la selección y el servidor calcula el precio, revisa colores permitidos y existencias.
- Comando `cargar_datos_demo` con un catálogo de ejemplo.
- 42 pruebas con pytest.

## Tienda (portada, categorías y kits)

- **Portada:** compra por categoría, kits navideños (productos de la categoría `kits` marcados como destacados) y "Así de fácil".
- **Listas con filtros** por talla (Niña/Adulto) y color: `/catalogo/sueteres/?talla=nina&color=12`.
- **Página de producto:** colores y tallas como botones (`static/js/producto.js`), tallas agotadas tachadas y **fecha estimada de entrega** (`catalogo/entregas.py`: días de elaboración + días de envío, solo días hábiles).
- **Kits:** se dan de alta como productos de la categoría *Kits navideños*; el campo *precio anterior* muestra el descuento.
- **Ayuda** (`/ayuda/`): políticas de envío, cambios y devoluciones, y cancelación.
- Mientras no haya fotos, los suéteres y calcetines se muestran con un dibujo de ejemplo en su color. Al subir una foto en el admin, se usa la foto.

## Cómo correrlo (Windows, macOS o Linux)

Requiere Python 3.11 o superior.

```bash
# 1. Crear y activar entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

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

## Pruebas

```bash
pytest
```

## Estructura

```
tiendaWeb/          configuración del proyecto (settings, urls)
catalogo/
  models.py         modelos del catálogo
  cotizacion.py     cálculo y validación de precios (lógica de negocio)
  views.py          páginas y API de cotización
  admin.py          panel de administración
  management/commands/cargar_datos_demo.py
  tests/            pruebas con pytest
templates/          HTML (Bootstrap 5)
static/css          estilos
static/js           cotizador.js (cotización en vivo), simulador.js (dibujo del moño)
                    y personalizador.js (pasos, Lo más vendido y Restablecer)
static/simulador/   capas del moño (PNG en gris), mapa del decorado y tiras de estampados
docs/bitacora.md    plan baseline vs. real
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

## Producción (PostgreSQL)

Basta con definir variables de entorno:

```
DATABASE_URL=postgres://usuario:clave@host:5432/moneria
DJANGO_SECRET_KEY=una-clave-larga-y-secreta
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=mi-tienda.onrender.com
```

## Equipo

- Santiago González Kevin
- Cardoso Martínez Josue
- Flores Herrera Oswaldo
