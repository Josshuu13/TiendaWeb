# Publicar la tienda

La configuración está en `render.yaml` y usa el plan gratuito de Render. Revisa sus límites actuales
antes de presentar: el servicio gratuito se duerme sin visitas y la primera carga tarda, así que
ábrelo unos minutos antes de la demostración.

## Primera publicación

1. En [Render](https://render.com), crea un **Blueprint** conectado a este repositorio.
2. Elige la rama `main`. Render crea la base de datos y la aplicación.
3. Agrega estas variables al servicio web solo para la primera publicación:
   `CARGAR_DEMO=1`, `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` y `DJANGO_SUPERUSER_PASSWORD`.
4. Cuando termine, borra esas cuatro variables. Si no, cada publicación restablecerá las existencias.

## Stripe en modo de pruebas

1. Crea una cuenta en [Stripe](https://dashboard.stripe.com) y activa el modo de pruebas.
2. Copia la llave secreta (`sk_test_...`) en `STRIPE_SECRET_KEY`.
3. En *Developers > Webhooks*, crea un destino hacia `https://TU-SITIO/pagos/webhook/` con los eventos
   `checkout.session.completed`, `checkout.session.async_payment_succeeded` y `checkout.session.expired`.
4. Copia el secreto (`whsec_...`) en `STRIPE_WEBHOOK_SECRET`.
5. Paga con la tarjeta de prueba `4242 4242 4242 4242`, cualquier fecha futura y cualquier CVC.

## Probar Stripe en tu computadora

Con la [CLI de Stripe](https://docs.stripe.com/stripe-cli) instalada:

```bash
stripe listen --forward-to 127.0.0.1:8000/pagos/webhook/
```

Copia el secreto que imprime en `STRIPE_WEBHOOK_SECRET` dentro de `.env` y reinicia el servidor.

## Revisión final

```bash
DJANGO_DEBUG=0 DJANGO_SECRET_KEY=una-clave-larga-de-prueba python manage.py check --deploy
```
