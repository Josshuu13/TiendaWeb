# Resultados de pruebas

Ejecución del 21 de noviembre de 2026, en la rama `feature/entrega-final`.

| Conjunto | Pruebas | Resultado | Tiempo |
|---|---|---|---|
| Automáticas (`pytest`) | 235 | 235 pasaron | 1 min 24 s |
| En navegador real (`pytest -m e2e`) | 3 | 3 pasaron | 10 s |
| **Total** | **238** | **Todas pasaron** | |

| Área | Pruebas |
|---|---|
| Catálogo, cotización, simulador, calcetas, temporadas y estándares | 130 |
| Pedidos, pagos con Stripe y posventa | 70 |
| Carrito | 22 |
| Cuentas | 13 |
| Recorrido en navegador (Playwright) | 3 |

GitHub Actions repite todas estas pruebas en cada Pull Request sobre **PostgreSQL**, además de
revisar el estilo del código, las migraciones y la configuración de seguridad para producción.

## Casos que pide el anteproyecto

| Caso del anteproyecto | Pruebas que lo cubren |
|---|---|
| Cotizaciones con distintas cantidades | `test_cantidad_fuera_de_rango`, `test_agregar_suma_piezas_y_junta_repetidos`, `test_precio_base_mas_diseno` |
| Configuraciones válidas | `test_combinaciones_tienen_las_seis_partes_y_se_pueden_cotizar`, `test_todos_los_disenos_de_ejemplo_se_pueden_cotizar`, `test_selecciones_invalidas_se_rechazan` |
| Productos agotados | `test_variante_agotada`, `test_producto_agotado_despues_marca_error`, `test_si_se_agota_mientras_compra_no_se_crea_nada` |
| Confirmaciones de pago repetidas | `test_confirmacion_repetida_no_duplica_nada`, `test_aviso_repetido_se_aplica_una_sola_vez` |
| Pedidos mixtos | `test_pedido_mixto_con_las_tres_lineas_toma_el_mas_tardado`, `test_compra_con_las_tres_lineas_y_calceta_personalizada`, `test_compra_completa_con_las_tres_lineas` (navegador) |
| Solicitudes de cancelación o devolución | `test_cancelacion_aprobada_repone_existencias`, `test_devolucion_solo_despues_de_entregado`, `test_cancelacion_solicitada_y_aprobada_en_el_admin` (navegador) |
| Cada cliente solo consulta sus pedidos | `test_un_pedido_ajeno_responde_404`, `test_mis_pedidos_solo_muestra_los_propios`, `test_mis_pedidos_exige_iniciar_sesion` |
| Las acciones administrativas requieren permisos | `test_cliente_normal_no_entra_al_admin`, `test_admin_no_puede_saltar_de_estado` |

## Criterios de aceptación

| Criterio | Prueba | Captura |
|---|---|---|
| Compra con las tres líneas de producto | `test_compra_completa_con_las_tres_lineas` | `capturas/05-carrito.png` |
| Visualizar y conservar una personalización | `test_la_personalizacion_se_conserva_aunque_cambie_el_catalogo` | `capturas/03-simulador-mono.png`, `capturas/04-personalizador-calceta.png` |
| Comprobar el importe calculado | `test_compra_crea_pedido_con_importes_del_servidor` | `capturas/06-finalizar-compra.png` |
| Verificar el pago de prueba | `test_aviso_firmado_confirma_el_pago` (simulado) | Compra con Stripe en modo de pruebas (capturas `stripe-*.png`) |
| Consultar la fecha propuesta | `test_pedido_mixto_con_las_tres_lineas_toma_el_mas_tardado` | `capturas/07-pedido-confirmado.png` |
| Registrar una solicitud de cancelación o devolución | `test_cancelacion_solicitada_y_aprobada_en_el_admin` | `capturas/08-admin-solicitudes.png`, `capturas/09-pedido-cancelado.png` |
| La administración refleja estado y disponibilidad | `test_admin_cambia_estado_y_captura_envio`, `test_cancelacion_aprobada_repone_existencias` | `capturas/09-pedido-cancelado.png` |

## Cómo repetir las pruebas

```bash
pip install -r requirements-dev.txt
playwright install chromium
pytest
pytest -m e2e
```

Para volver a generar las capturas:

```bash
GUARDAR_CAPTURAS=1 pytest -m e2e
```

## Lo que estas pruebas no cubren

- El pago con una cuenta real de Stripe en modo de pruebas: las pruebas simulan sus respuestas
  y firmas. Se verifica con `python manage.py verificar_stripe` y una compra de prueba.
- La concurrencia real: en local se usa SQLite, que no bloquea filas. GitHub Actions corre las
  pruebas en PostgreSQL, pero no simula dos compras al mismo tiempo.
- La tienda publicada en internet: la configuración de producción se probó en local con Gunicorn.
