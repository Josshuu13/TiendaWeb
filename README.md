# Moñería – Tienda web de moños personalizables

Proyecto de **Negocios Electrónicos y Desarrollo Web** (Facultad de Ingeniería, UNAM).
Tienda B2C de moños para niña con simulador visual, más suéteres y calcetines navideños.

## Qué hay hasta ahora

- Proyecto Django `tiendaWeb` con la app `catalogo`.
- Modelos: `Categoria`, `Color`, `Producto`, `Variante` (talla, color y existencias), `Parte` (capas del moño) y `Decoracion`.
- Panel de administración en español (`/admin/`).
- Páginas: inicio, catálogo por categoría y detalle de producto.
- **Cotización validada en el servidor** (`/api/cotizar/`): el navegador solo manda la selección y el servidor calcula el precio, revisa colores permitidos y existencias.
- Comando `cargar_datos_demo` con un catálogo de ejemplo.
- 22 pruebas con pytest.

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
static/css, js      estilos y cotizador.js
docs/bitacora.md    plan baseline vs. real
```

## Formato de la selección (catálogo → cotización → carrito)

El cliente **nunca** manda precios; solo identificadores.

```json
{ "producto": "sueter-reno", "variante": "SUETER-RENO-M-ROJ", "cantidad": 2 }

{ "producto": "mono-clasico",
  "opciones": { "lazos": 3, "nudo": 5, "decoracion": "perla" },
  "cantidad": 1 }
```

En el moño, `lazos` y `nudo` son el **id** del color y `decoracion` es la **clave** de la decoración.

## Conexión con el simulador

`static/js/cotizador.js` emite el evento `seleccion-cambiada` cada vez que el cliente cambia un color:

```js
document.addEventListener("seleccion-cambiada", (e) => {
  // e.detail.colores   -> { lazos: "#B3122E", nudo: "#F4F4F0" }
  // e.detail.decoracion -> "perla" | null
});
```

El simulador con fotos solo tiene que escuchar este evento y redibujar el canvas dentro de `<div id="simulador">`.
Las capas PNG se suben en el admin, en cada **Parte** del moño.

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
