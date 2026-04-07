import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("usuario", "0001_initial"),
        ("atencion_cliente", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="reclamo",
            name="empleado_asignado",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"rol": "empleado"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reclamos_asignados",
                to="usuario.usuario",
            ),
        ),
    ]
