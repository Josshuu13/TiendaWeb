# Monto a partir del cual el envío es gratis (se edita en Configuración de la tienda).

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuraciontienda",
            name="envio_gratis_desde",
            field=models.DecimalField(
                decimal_places=2,
                default=300,
                help_text="Si el subtotal llega a este monto, el envío es gratis. Pon 0 para no ofrecer envío gratis.",
                max_digits=8,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="envío gratis desde",
            ),
        ),
    ]
