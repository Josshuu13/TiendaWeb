# Arquitectura de Pretexto

## Diagrama de contexto

```mermaid
flowchart LR
    Cliente([Cliente]) -->|navega y compra| Tienda[Tienda web Django]
    Equipo([Equipo de la tienda]) -->|catálogo, pedidos y envíos| Tienda
    Tienda -->|crea la sesión de pago| Stripe[Stripe modo de pruebas]
    Cliente -->|escribe su tarjeta| Stripe
    Stripe -->|aviso firmado por webhook| Tienda
    Tienda -->|avisos del pedido| Correo[Servicio de correo]
    Cliente -->|soporte con ID de pedido| WhatsApp[WhatsApp]
    Tienda --- BD[(PostgreSQL)]
```

## Capas

| Capa | Dónde vive | Responsabilidad |
|---|---|---|
| Interfaz | `templates/`, `static/` | HTML desde el servidor, CSS propio, simulador en canvas y HTMX |
| Lógica de negocio | `catalogo/cotizacion.py`, `catalogo/entregas.py`, `carrito/carrito.py`, `pedidos/servicios.py` | Precios, existencias, fechas, estados y reembolsos |
| Almacenamiento | `*/models.py` | SQLite en desarrollo y PostgreSQL en producción |

## Modelo de datos

```mermaid
erDiagram
    CATEGORIA ||--o{ PRODUCTO : agrupa
    PRODUCTO ||--o{ VARIANTE : tiene
    PRODUCTO ||--o{ PARTE : "tiene capas"
    PRODUCTO ||--o{ COMBINACION : ofrece
    TEMPORADA }o--o{ PRODUCTO : presenta
    PRODUCTO }o--o{ ESTAMPADO : admite
    COLOR ||--o{ VARIANTE : pinta
    PARTE }o--o{ COLOR : permite
    COMBINACION ||--o{ COMBINACIONPARTE : define
    USUARIO ||--o{ PEDIDO : realiza
    PEDIDO ||--|{ LINEAPEDIDO : contiene
    PEDIDO ||--|{ EVENTOPEDIDO : registra
    PEDIDO ||--o{ SOLICITUDPOSVENTA : recibe
    PRODUCTO |o--o{ LINEAPEDIDO : "se copia en"
    VARIANTE |o--o{ LINEAPEDIDO : aparta

    PEDIDO {
        string folio UK
        string estado
        decimal subtotal
        decimal costo_envio
        decimal total
        date entrega_maxima
        string transportista
        string numero_guia
        string telefono_transportista
    }
    LINEAPEDIDO {
        string nombre
        json seleccion
        json opciones
        decimal precio_unitario
        int cantidad
    }
    SOLICITUDPOSVENTA {
        string tipo
        string estado
        text motivo
    }
```

`ConfiguracionTienda` guarda el costo de envío y los datos de soporte. `EventoPago` guarda los
avisos ya procesados de Stripe.

## Estados del pedido

```mermaid
stateDiagram-v2
    [*] --> PendienteDePago
    PendienteDePago --> Confirmado: Stripe confirma el pago
    PendienteDePago --> Cancelado: abandono o tiempo agotado
    Confirmado --> EnPreparacion
    Confirmado --> Cancelado: solicitud aprobada
    EnPreparacion --> Enviado: con transportista y guía
    Enviado --> EnCamino
    EnCamino --> Entregado
    Entregado --> Devuelto: solicitud aprobada
```

## Recorrido de compra

```mermaid
sequenceDiagram
    actor C as Cliente
    participant T as Tienda
    participant S as Stripe
    C->>T: Agrega productos (solo identificadores)
    T->>T: Cotiza con precios del servidor
    C->>T: Confirma dirección
    T->>T: Crea el pedido y aparta existencias
    T->>S: Crea la sesión de pago
    C->>S: Paga con su tarjeta
    S-->>T: Webhook firmado
    T->>T: Verifica firma, importe y repetidos
    T-->>C: Pedido confirmado y seguimiento
```

## Decisiones técnicas

| Decisión | Por qué |
|---|---|
| Django con HTML desde el servidor | Es lo que promete el anteproyecto. Amazon, Apple, Huawei y Mercado Libre también envían el HTML armado |
| CSS propio en lugar de Bootstrap | Da la identidad visual buscada y evita cargar código que no se usa |
| HTMX | Actualiza el carrito sin recargar y sin una segunda aplicación en JavaScript |
| Carrito en sesión | Solo guarda selecciones; precios y existencias se recalculan siempre |
| Stripe Checkout | La tarjeta se captura en Stripe, así que nunca llega a este servidor |
| Webhook firmado y registro de eventos | El pago no depende de la pantalla del cliente y una confirmación repetida no se aplica dos veces |
| Existencias apartadas con una condición en el UPDATE | Dos compras simultáneas no pueden vender la última pieza |
| Lógica en `servicios.py` | Cliente, admin y Stripe pasan por las mismas reglas, y se pueden probar sin navegador |
| Folio aleatorio y 404 en pedidos ajenos | No revela cuántas ventas hay y no permite adivinar pedidos de otras personas |
| Sin recursos de terceros en el navegador | Permite una política de seguridad estricta y protege la privacidad |
