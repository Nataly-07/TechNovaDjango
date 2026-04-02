from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("producto", "0007_alter_productoimagen_activa_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="precio_promocion",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
        migrations.AddField(
            model_name="producto",
            name="fecha_fin_promocion",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]

