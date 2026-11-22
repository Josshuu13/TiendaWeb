"""
Revisa la configuración de Stripe sin cobrar nada.

    python manage.py verificar_stripe

Comprueba que la llave sea de modo de pruebas, que exista el secreto del webhook y que
Stripe acepte la llave. Para eso consulta el saldo de la cuenta de pruebas, una operación
de solo lectura.
"""
import stripe
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse


class Command(BaseCommand):
    help = "Revisa la configuración de Stripe en modo de pruebas sin cobrar nada."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sin-conexion", action="store_true",
            help="Solo revisa las variables de entorno; no se conecta a Stripe.",
        )

    def handle(self, *args, **opciones):
        llave = settings.STRIPE_SECRET_KEY
        secreto = settings.STRIPE_WEBHOOK_SECRET

        if not llave:
            raise CommandError(
                "Falta STRIPE_SECRET_KEY en el archivo .env. Sin ella, la tienda usa el pago simulado."
            )
        if llave.startswith(("sk_live_", "rk_live_")):
            raise CommandError(
                "La llave es de modo real (sk_live_). Para el proyecto usa la de modo de pruebas (sk_test_)."
            )
        if not llave.startswith(("sk_test_", "rk_test_")):
            raise CommandError("STRIPE_SECRET_KEY no parece una llave de Stripe: debe empezar con sk_test_.")
        self.stdout.write(self.style.SUCCESS("✓ La llave es de modo de pruebas."))

        if not opciones["sin_conexion"]:
            try:
                stripe.Balance.retrieve(api_key=llave)
            except stripe.AuthenticationError as e:
                raise CommandError("Stripe rechazó la llave. Cópiala de nuevo desde el dashboard.") from e
            except stripe.StripeError as e:
                raise CommandError(f"No se pudo hablar con Stripe: {e.user_message or e}") from e
            self.stdout.write(self.style.SUCCESS("✓ Stripe aceptó la llave."))

        if not secreto:
            raise CommandError(
                "Falta STRIPE_WEBHOOK_SECRET: Stripe no podrá confirmar los pagos. "
                "En tu computadora lo imprime `stripe listen`; en internet sale del dashboard."
            )
        if not secreto.startswith("whsec_"):
            raise CommandError("STRIPE_WEBHOOK_SECRET debe empezar con whsec_.")
        self.stdout.write(self.style.SUCCESS("✓ Hay secreto para verificar los avisos de Stripe."))

        self.stdout.write(f"Los avisos deben llegar a: {settings.SITIO_URL}{reverse('pedidos:webhook')}")
        self.stdout.write(self.style.SUCCESS("Listo: los pagos de prueba se confirmarán con Stripe."))
