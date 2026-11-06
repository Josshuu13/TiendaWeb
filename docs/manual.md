# Manual breve de uso

## Para el cliente

1. **Elige.** Diseña tu moño en el simulador o escoge la talla de un producto.
2. **Agrega al carrito.** El precio lo calcula el servidor.
3. **Entra o crea tu cuenta.** Se pide al finalizar la compra.
4. **Escribe tu dirección y paga.** En esta demo el pago es de prueba.
5. **Sigue tu entrega** en *Mis pedidos*: ID de pedido, línea de tiempo, transportista y guía.
6. **¿Necesitas ayuda?** Usa el botón de WhatsApp del pedido; el mensaje ya incluye tu ID.
7. **¿Quieres cancelar o devolver?** Envía la solicitud desde tu pedido.

## Para el equipo de la tienda

Entra a `/admin/`.

**Avanzar un pedido.** En *Pedidos*, abre uno y elige el nuevo estado. El menú solo muestra los
cambios permitidos. Para marcarlo como Enviado, primero captura transportista y número de guía.
También puedes elegir varios pedidos en la lista y usar *Avanzar al siguiente estado*.

**Datos de prueba para la demo.** Elige el pedido y usa *Asignar transportista de prueba*.

**Resolver solicitudes.** En *Solicitudes de cancelación o devolución*, elige una y usa *Aprobar* o
*Rechazar*. Al aprobar, el pedido cambia de estado y las piezas regresan al inventario.

**Cambiar envío y soporte.** En *Configuración de la tienda* se editan el costo de envío, el teléfono,
el WhatsApp y el horario. Los números iniciales son ficticios.

**Agregar cualquier producto.** No hace falta programar:

1. Si es de un tipo nuevo, crea su categoría en *Categorías*. Aparece sola en el menú.
2. En *Productos > Añadir*, escribe nombre, categoría, precio y días de elaboración, y sube su foto.
3. En la tabla de abajo agrega una variante por cada talla o color, con sus existencias. Si solo
   hay una versión, deja "Unitalla" y escribe las existencias. El SKU se genera solo.
4. Marca *Destacado* si quieres que salga en la portada.

**Cambiar de temporada.** En *Temporadas > Añadir*, escribe el aviso de la franja, el título, la
imagen y los productos, y marca *Activa*. Puedes poner fechas de inicio y fin para que entre y salga
sola. Si termina una temporada, sus productos siguen en el catálogo hasta que los desactives.

Ejemplo para regreso a clases: aviso "Esta temporada, el pretexto es regreso a clases", título
"Ya casi empiezan las clases" y fechas del 1 al 31 de agosto.

## Guion para la demostración

1. Compra un moño personalizado, un suéter y unos calcetines en un mismo pedido.
2. Muestra el importe calculado, la fecha estimada y el pago de prueba.
3. Abre el pedido en *Mis pedidos*.
4. En el admin, asigna el transportista de prueba y avanza el estado.
5. Recarga el pedido para ver la línea de tiempo, la guía y el teléfono del transportista.
6. Registra una solicitud de cancelación en otro pedido y apruébala en el admin.
7. Muestra que las existencias regresaron en *Variantes*.
