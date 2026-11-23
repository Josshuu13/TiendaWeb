# Bitácora: plan baseline vs. real

Registro para la sección "Plan de trabajo (baseline vs. Real)" de la entrega final.
Fecha de entrega final: **noviembre de 2026** (la fecha planeada era el 20 de noviembre).

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
| 04/11/2026 | Catálogo de 5 suéteres (el anteproyecto proponía hasta 4); un sexto no se generó porque se agotaron los créditos de Canva. Sus imágenes se generaron con IA en Canva y el fondo se quitó localmente. | Se pidió mostrar solo la prenda. Son referencias visuales de la demo, no fotografías de productos reales. El 22/11 se reemplazaron por los originales en alta calidad. |
| 05/11/2026 | La tienda cambia de nombre a **Pretexto** y deja de depender de Navidad: categorías, portada, aviso y temporadas se administran desde el panel. | El equipo quiere usarla después con los productos que tenga en cada temporada. "Moñería" limitaba la marca y ya se usaba un nombre parecido en el mercado. |
| 08/11/2026 | Paleta de 26 colores: se agregan jade, naranja, palo de rosa, café arena y azul turquesa, y un aviso para pedir por WhatsApp un color que no esté. | Los clientes piden tonos fuera de la paleta. Se prefirió una lista fija a un selector libre de color porque solo se pueden ofrecer listones que realmente existen. |
| 08/11/2026 | La página de Moños se divide en **Diseña el tuyo** (moño personalizable) y **Diseños listos para usar** (8 moños de uniforme a precio menor). Se retira el "Moño escolar" de 4 colores y el filtro de color de esta categoría. | El filtro escondía el moño personalizable. Los diseños listos atienden a quien solo quiere el moño del uniforme; sus imágenes se generan con las capas del simulador (`generar_imagenes_monos`). |
| 15/11/2026 | Catálogo de calcetines: 8 diseños nuevos (afelpados y de algodón, unitalla, con precio de oferta) en lugar de los 2 de ejemplo. Se capturan en `cargar_datos_demo` y sus fotos van en `static/img/calcetines/`; se retiran del repositorio el fixture `catalogo.json` y la carpeta `media/`. | Una sola fuente del catálogo para todo el equipo, las pruebas y el despliegue. Render borra `media/` en cada publicación. |
| 15/11/2026 | Decorados estampados: de 2 a **18 diseños con 82 variantes de color**, agrupados en Escolares, Navideños y Otros, a +$15 (precio provisional). Fotos propias del listón, enderezadas y recortadas; los listones calados, transparentes y metálicos se corrigieron (huecos rellenos, luz pareja) y los diseños de dos tonos se recolorearon. Se descartan listones con personajes con licencia (princesas, Masha y el Oso, Gabby's Dollhouse, Winnie Pooh, Mickey). | Más opciones sin saturar la página: el cliente elige primero el diseño (una punta de listón) y luego su color. Los personajes tienen derechos de autor y marca registrada y la tienda se publica en internet. |
| 17/11/2026 | Moños listos en 3 secciones: **Navideños** (4), **Uniforme escolar** (8) y **Con decorado** (8), con una barra "Categorías:" de atajos que se queda fija al bajar. Las imágenes de los moños con estampado se generan con las capas del simulador (`generar_imagenes_monos`). | Con 20 moños listos una sola cuadrícula era larga; las secciones y los atajos permiten llegar directo a lo que se busca, y Navideños va primero por la temporada. |
| 20/11/2026 | Precios ajustados con una comparación de mercado (Mercado Libre, Liverpool, Etsy): moño de uniforme $60, navideño o con decorado $75, personalizable $70 (+$15 con estampado). Envío a domicilio $99 y **gratis desde $300**, con barra "Te faltan $X" en el carrito. La foto de los productos ya no se desplaza al bajar. | Un moño suelto con envío casi duplicaba su precio; el envío gratis por monto motiva a comprar varias piezas o un kit, y la guía de paquetería cuesta lo mismo para uno o varios moños. |
| 20/11/2026 | Kits navideños rehechos: 5 kits (Santa, Muñeco de nieve, Renos, Osito y Mini) armados con productos reales de la tienda. Cada kit muestra lo que incluye, se compra en las tallas de su suéter y su precio tachado es la suma de las piezas (ahorro real de $20 a $66). Imágenes generadas con `generar_imagenes_kits`. | Los kits anteriores mencionaban productos retirados y no permitían elegir la talla del suéter. |
| 21/11/2026 | Se construye el **personalizador de calcetas** que pedía el anteproyecto: color de la calceta y de sus detalles, 6 diseños predefinidos, posición, tamaño y talla, con precio validado en el servidor. Revierte la decisión del 26/10. | Era un objetivo específico del anteproyecto. Con el moño terminado hubo tiempo para hacerlo sin sacrificar calidad. Es una vista 2D dibujada en canvas, como proponía el anteproyecto ("representación 2D"). |
| 21/11/2026 | La calceta del personalizador deja de ser un dibujo: ahora es un **render de Blender** de una calceta de tejido acostada, con la silueta de los calcetines Santa Claus del catálogo, puntadas, resorte en el puño, pliegues y luz de estudio. Se separa en capas (cuerpo; puño, talón y punta; sombra) y se pinta igual que el moño. Fuentes en `docs/simulador-calceta/`. Los diagramas se rehacen con un estilo propio de la tienda (etiquetas de ropa, hilos cosidos y mapa de metro). | El dibujo se veía falso junto al moño fotográfico y la foto del catálogo era muy pequeña (bordes irregulares al ampliarla). La lógica, los precios y las validaciones no cambian. |
| 21/11/2026 | Pruebas en navegador real con **Playwright**: compra con las tres líneas, cancelación aprobada en el admin y uso en celular. Generan las capturas de `docs/capturas/`. | Era la tarea planeada para el 18/11; las capturas sustituyen al mockup de Figma como evidencia de las pantallas. |
| 21/11/2026 | Comando `verificar_stripe` para comprobar la configuración de pagos sin cobrar nada, y simulación local de producción con Gunicorn. | Deja lista la verificación del pago de prueba con el proveedor, que exige el anteproyecto. |
| 22/11/2026 | Fotos de los 5 suéteres reemplazadas por las originales de Canva (unos 900 px en lugar de 185 px) y kits regenerados con `generar_imagenes_kits`. Documento final y presentación reorganizados según la lista de la entrega final (objetivos, producto, mercado, estrategia, plan, mockup, arquitectura, tecnología, propuesta de negocio, demo con pruebas y fuentes APA), con guion de 15 minutos. La demostración usa el pago simulado. | Los suéteres se veían borrosos y el profesor publicó los puntos que se evalúan y la duración de la presentación. |
| 22/11/2026 | Cierre del proyecto. El pago se verifica con una cuenta de Stripe en modo de pruebas y la tarjeta 4242; la demostración en vivo usa el pago simulado para no depender del internet del salón. La tienda **no se publica**: la configuración de producción está probada en local y documentada, pero no se expone un sitio de demostración en internet. La encuesta queda diseñada y su aplicación pasa a trabajo futuro. Los cambios de alcance de esta bitácora se presentan en el documento final y en la presentación. | Los sitios recién publicados atraen robots que buscan fallas; para una entrega académica no hacía falta exponerlo. La verificación del pago y la demostración cubren los criterios de aceptación. |

## Seguimiento de tareas

Los responsables se tomaron del historial de Git (autor de cada commit y Pull Request).

| Tarea | Responsable | Fecha prevista | Fecha real | Evidencia |
|---|---|---|---|---|
| Proyecto Django y modelos del catálogo | Cardoso Martínez Josue | 01/11 | 26/10 | Commit inicial (`df9ef57`) |
| Catálogo visible y cotización validada | Cardoso Martínez Josue | 01/11 | 26/10 | `catalogo/cotizacion.py` y pruebas |
| Fotos del moño y capas PNG | Cardoso Martínez Josue | 01/11 | 02/11 | 6 capas en `static/simulador` |
| Prototipo del simulador (fotos o SVG) | Cardoso Martínez Josue | 01/11 | 02/11 | Pruebas de color con fotos |
| Mockup | Santiago González Kevin | 01/11 | 21/11 | Sustituido por el prototipo funcional y las capturas de `docs/capturas/` |
| Diagrama de contexto y modelo de datos | Santiago González Kevin | 01/11 | 04/11 | `docs/arquitectura.md` |
| Simulador integrado en Django | Cardoso Martínez Josue | 08/11 | 03/11 | `simulador.js` y pruebas |
| Carrito mixto | Santiago González Kevin | 08/11 | 04/11 | `carrito/` y pruebas automáticas |
| Pedidos y fecha de entrega | Santiago González Kevin (fecha de entrega: Cardoso Martínez Josue) | 15/11 | 04/11 | `pedidos/` y `catalogo/entregas.py` |
| Pago con Stripe (webhook) | Santiago González Kevin | 15/11 | 04/11 código; verificación en modo de pruebas el 22/11 | `pedidos/pagos.py`, `verificar_stripe` y pruebas |
| Cancelación y devolución | Santiago González Kevin | 15/11 | 04/11 | `pedidos/servicios.py` y pruebas automáticas |
| Cuentas, seguimiento de entrega y soporte | Santiago González Kevin | 15/11 | 04/11 | `cuentas/`, `templates/pedidos/detalle.html` |
| Rediseño de la interfaz y nombre Pretexto | Santiago González Kevin | 15/11 | 05/11 | `static/css/tienda.css`, temporadas en el admin |
| Catálogo de calcetines con fotos | Flores Herrera Oswaldo y Santiago González Kevin | 15/11 | 08/11 | `static/img/calcetines/` |
| Paleta de 26 colores y moños listos | Cardoso Martínez Josue | 15/11 | 08/11–19/11 | PR #3, #6 y #7 |
| Decorados estampados (18 diseños) | Cardoso Martínez Josue | 15/11 | 17/11 | PR #5 |
| Precios, envío gratis y kits | Cardoso Martínez Josue | 20/11 | 20/11 | PR #8 |
| Personalizador de calcetas | Santiago González Kevin | 08/11 | 21/11 | `static/js/calceta.js`, `static/simulador/calceta/`, `docs/simulador-calceta/`, `catalogo/tests/test_calcetas.py` |
| Pruebas Playwright del recorrido | Santiago González Kevin | 18/11 | 21/11 | `e2e/` y `docs/resultados-pruebas.md` |
| Despliegue en PaaS | Santiago González Kevin | 15/11 | Configuración probada en local el 21/11; no se publica por decisión del equipo (22/11) | `render.yaml`, `docs/publicacion.md` |
| Investigación de mercado | Cardoso Martínez Josue y Santiago González Kevin | 01/11 | 20/11 | `docs/investigacion-de-mercado.md` |
| Documento final, presentación y guion | Equipo | 20/11 | 22/11 | `docs/entrega/` |
