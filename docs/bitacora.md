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
| 26/10/2026 | Calendario comprimido de 8 a ~4 semanas restantes. | Fecha de entrega final: 20/11/2026. |

## Seguimiento de tareas

| Tarea | Responsable | Fecha prevista | Fecha real | Evidencia |
|---|---|---|---|---|
| Proyecto Django y modelos del catálogo | | 01/11 | 26/10 | Commit inicial |
| Catálogo visible y cotización validada | | 01/11 | 26/10 | 22 pruebas pytest |
| Fotos del moño y capas PNG | | 01/11 | | |
| Prototipo del simulador (fotos o SVG) | | 01/11 | | |
| Mockup en Figma | | 01/11 | | |
| Diagrama de contexto y modelo de datos | | 01/11 | | |
| Simulador integrado en Django | | 08/11 | | |
| Carrito mixto | | 08/11 | | |
| Pedidos y fecha de entrega | | 15/11 | | |
| Pago con Stripe (webhook) | | 15/11 | | |
| Cancelación y devolución | | 15/11 | | |
| Despliegue en PaaS | | 15/11 | | |
| Pruebas Playwright del recorrido | | 18/11 | | |
| Documento final y presentación | | 20/11 | | |
