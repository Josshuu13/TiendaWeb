# Diseños de estampado en varios colores: cada estampado indica su diseño, su grupo
# (Escolares, Navideños, Otros) y el color de la variante.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0005_temporadas_y_catalogo_general'),
    ]

    operations = [
        migrations.AddField(
            model_name='estampado',
            name='diseno',
            field=models.CharField(blank=True, help_text='Los estampados con el mismo diseño se muestran juntos (por ejemplo, "Mariposas"). Si se deja vacío, el estampado es su propio diseño.', max_length=40, verbose_name='diseño'),
        ),
        migrations.AddField(
            model_name='estampado',
            name='grupo',
            field=models.CharField(choices=[('escolar', 'Escolares'), ('navideno', 'Navideños'), ('otro', 'Otros')], default='otro', max_length=10),
        ),
        migrations.AddField(
            model_name='estampado',
            name='color_nombre',
            field=models.CharField(blank=True, help_text='Color de esta variante del diseño ("Lila"). Vacío si el diseño tiene un solo color.', max_length=30, verbose_name='color'),
        ),
        migrations.AddField(
            model_name='estampado',
            name='color_hex',
            field=models.CharField(blank=True, help_text='Color del circulito que representa esta variante, por ejemplo #A98BD3.', max_length=7, verbose_name='código de color'),
        ),
    ]
