import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orden", "0002_solicitud_oc_prov"),
        ("usuario", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="detalleorden",
            name="cantidad_recibida",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Cantidad física ingresada al inventario en la validación de recepción.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="ordencompra",
            name="observaciones_recepcion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="ordencompra",
            name="recepcion_validada_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="ordencompra",
            name="recepcion_validada_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ordenes_compra_recepciones_validadas",
                to="usuario.usuario",
            ),
        ),
        migrations.AlterField(
            model_name="ordencompra",
            name="estado",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente"),
                    ("recibida", "Recibida"),
                    ("completada", "Completada"),
                    ("cancelada", "Cancelada"),
                ],
                default="pendiente",
                max_length=20,
            ),
        ),
    ]
