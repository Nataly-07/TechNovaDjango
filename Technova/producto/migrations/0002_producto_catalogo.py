from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("producto", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="producto",
            name="categoria",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="producto",
            name="marca",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="producto",
            name="descripcion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="producto",
            name="precio_venta",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
    ]
