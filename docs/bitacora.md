# Bitácora: plan baseline vs. real

Registro para la sección "Plan de trabajo (baseline vs. Real)" de la entrega final.
Fecha de entrega final: **20 de noviembre de 2026**.

## Cambios respecto al anteproyecto

| Fecha | Cambio | Justificación |
|---|---|---|
| 26/10/2026 | Se reinicia el código desde cero. | El código previo no reflejaba el modelo de datos definitivo (faltaban variantes, existencias y capas del moño). |
| 26/10/2026 | Solo el moño tiene personalizador; las calcetas se venden desde catálogo con talla y color. | Control de alcance: un personalizador bien hecho en lugar de dos incompletos. Los criterios de aceptación solo exigen visualizar y conservar una personalización. |
| 26/10/2026 | El simulador usa fotografías reales por capas recoloreadas con canvas, en lugar de SVG. | Mayor realismo (textura y sombras del listón) y mayor valor agregado. Plan B: SVG si el 1/11 el recoloreo no es convincente. |
| 26/10/2026 | Pasarela definida: Stripe en modo de pruebas. | El anteproyecto dejaba el proveedor abierto. |
| 02/11/2026 | Sesión de fotos del moño en listón gris; decisión final: **fotos por capas** (no SVG). | El recoloreo conserva textura y sombras; se ve realista en colores claros y oscuros. |
| 02/11/2026 | El moño pasa de 2 partes (lazos, nudo) a **6 partes**: patas, base de abajo, base de arriba, decorado, tiras y nudo. | Corresponde a la estructura real del moño y permite combinaciones como la de los moños escolares de dos colores. |
| 03/11/2026 | Se reemplazan las decoraciones (perla, cascabel, copo) por **decorados estampados** (listones decorados). | Es lo que realmente se vende; cada estampado nuevo solo requiere una foto del listón. |
| 03/11/2026 | Paleta de 21 colores agrupada en **escolares, navideños y básicos**. | Responde al mercado objetivo: uniforme escolar y temporada navideña. |
| 04/11/2026 | Personalizador **paso a paso** (6 pasos con Anterior/Siguiente), resaltado de la parte en el moño, Restablecer, zoom y botón **Lo más vendido**. | Simplifica la experiencia: el cliente no se pierde entre 6 partes y entiende qué pieza cambia. |
| 05/11/2026 | Rediseño de la tienda: portada por categorías, sección de **kits navideños**, filtros, tallas como botones, fecha estimada de entrega y página de políticas. | Navegación más simple; el Kit Navideño (valor agregado) queda visible; la fecha de entrega y las políticas de devolución son requisitos del proyecto. |
| 26/10/2026 | Calendario comprimido de 8 a ~4 semanas restantes. | Fecha de entrega final: 20/11/2026. |
| 04/11/2026 | Interfaz rediseñada con CSS propio, sin Bootstrap, con HTMX y tipografía Inter. | Identidad visual inspirada en tiendas premium; mejor rendimiento y una política de seguridad más estricta. Se conserva Django con HTML, CSS y JavaScript, como indica el anteproyecto. |
| 04/11/2026 | Se agrega seguimiento de entrega: ID de pedido, línea de tiempo, transportista, guía y teléfonos, simulados desde el admin. | Amplía la "consulta de pedidos" del anteproyecto con la experiencia de Amazon y Mercado Libre. |
| 04/11/2026 | Se agrega soporte técnico por WhatsApp con el ID del pedido. | Requisito nuevo. El número se cambia desde el admin. No se usa chatbot porque el alcance excluye inteligencia artificial en la aplicación. |
| 04/11/2026 | Cuenta obligatoria para comprar. | Permite cumplir que cada cliente solo consulte sus pedidos. |
| 04/11/2026 | Envíos a todo México con tarifa fija editable (antes: CDMX y zona metropolitana). | Simplifica la compra y el cálculo del costo. |
| 04/11/2026 | Catálogo de 5 suéteres (el anteproyecto proponía hasta 4); un sexto queda pendiente. Sus imágenes se generaron con IA en Canva y el fondo se quitó localmente. | Se pidió mostrar solo la prenda. Son referencias visuales de la demo, no fotografías de productos reales. Las versiones actuales son de 200 px y deben reemplazarse por los originales. |
| 05/11/2026 | La tienda cambia de nombre a **Pretexto** y deja de depender de Navidad: categorías, portada, aviso y temporadas se administran desde el panel. | El equipo quiere usarla después con los productos que tenga en cada temporada. "Moñería" limitaba la marca y ya se usaba un nombre parecido en el mercado. |
| 04/11/2026 | Pendiente: informar al profesor los cambios de alcance de esta bitácora. | El personalizador de calcetas sigue fuera de alcance y los calcetines y kits conservan dibujos de ejemplo. |

## Seguimiento de tareas

| Tarea | Responsable | Fecha prevista | Fecha real | Evidencia |
|---|---|---|---|---|
| Proyecto Django y modelos del catálogo | | 01/11 | 26/10 | Commit inicial |
| Catálogo visible y cotización validada | | 01/11 | 26/10 | 22 pruebas pytest |
| Fotos del moño y capas PNG | | 01/11 | 02/11 | 6 capas en static/simulador |
| Prototipo del simulador (fotos o SVG) | | 01/11 | 02/11 | Pruebas de color con fotos |
| Mockup en Figma | | 01/11 | | |
| Diagrama de contexto y modelo de datos | | 01/11 | 04/11 | docs/arquitectura.md |
| Simulador integrado en Django | | 08/11 | 03/11 | simulador.js + 28 pruebas |
| Carrito mixto | | 08/11 | 04/11 | carrito/ y pruebas automáticas |
| Pedidos y fecha de entrega | | 15/11 | 04/11 | pedidos/ y pruebas automáticas |
| Pago con Stripe (webhook) | | 15/11 | 04/11 (falta probar con llaves de Stripe) | pedidos/pagos.py y pruebas simuladas |
| Cancelación y devolución | | 15/11 | 04/11 | pedidos/servicios.py y pruebas automáticas |
| Despliegue en PaaS | | 15/11 | Archivos listos; falta publicar | render.yaml y docs/publicacion.md |
| Pruebas Playwright del recorrido | | 18/11 | | |
| Soporte técnico y seguimiento de entrega | | 15/11 | 04/11 | templates/pedidos/detalle.html |
| Rediseño de la interfaz | | 15/11 | 04/11 | static/css/tienda.css |
| Documento final y presentación | | 20/11 | | |
