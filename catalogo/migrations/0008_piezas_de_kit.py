# Piezas de un kit: qué productos de la tienda incluye cada kit navideño.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0007_producto_coleccion"),
    ]

    operations = [
        migrations.CreateModel(
            name="PiezaKit",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("orden", models.PositiveSmallIntegerField(default=0)),
                (
                    "kit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="piezas",
                        to="catalogo.producto",
                    ),
                ),
                (
                    "producto",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="en_kits",
                        to="catalogo.producto",
                    ),
                ),
            ],
            options={
                "verbose_name": "pieza del kit",
                "verbose_name_plural": "piezas del kit",
                "ordering": ["orden", "pk"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("kit", "producto"), name="pieza_unica_por_kit"
                    )
                ],
            },
        ),
    ]
