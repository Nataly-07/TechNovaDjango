import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("atencion_cliente", "0002_reclamo_empleado_asignado"),
        ("mensajeria", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="mensajeempleado",
            name="reclamo",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="mensajes_staff_chat",
                to="atencion_cliente.reclamo",
            ),
        ),
    ]
