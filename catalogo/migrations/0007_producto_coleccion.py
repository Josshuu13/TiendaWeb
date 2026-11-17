# Colección de un producto: sección de la página de Moños donde aparece
# (Navideños, Uniforme escolar o Con decorado).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0006_estampado_diseno_y_color'),
    ]

    operations = [
        migrations.AddField(
            model_name='producto',
            name='coleccion',
            field=models.CharField(blank=True, choices=[('navideno', 'Navideños'), ('uniforme', 'Uniforme escolar'), ('decorado', 'Con decorado')], help_text='Sección donde aparece en la página de Moños. Vacío: sin sección.', max_length=10, verbose_name='colección'),
        ),
    ]
