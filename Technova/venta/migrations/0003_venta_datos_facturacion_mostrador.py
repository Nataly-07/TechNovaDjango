# Generated manually for POS mostrador (datos de factura sin crear cuenta de cliente).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("venta", "0002_venta_tipo_venta_empleado_admin"),
    ]

    operations = [
        migrations.AddField(
            model_name="venta",
            name="datos_facturacion_mostrador",
            field=models.JSONField(
                blank=True,
                null=True,
                verbose_name="Datos de facturación (mostrador, sin cuenta)",
            ),
        ),
    ]
