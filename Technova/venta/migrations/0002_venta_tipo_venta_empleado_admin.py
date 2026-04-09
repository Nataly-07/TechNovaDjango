from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("usuario", "0001_initial"),
        ("venta", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="venta",
            name="tipo_venta",
            field=models.CharField(
                choices=[("online", "Online"), ("fisica", "Física")],
                default="online",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="venta",
            name="empleado",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ventas_fisicas_realizadas",
                to="usuario.usuario",
            ),
        ),
        migrations.AddField(
            model_name="venta",
            name="administrador",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ventas_registradas_como_admin",
                to="usuario.usuario",
            ),
        ),
    ]

