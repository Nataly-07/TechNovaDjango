from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("producto", "0002_producto_catalogo"),
    ]

    operations = [
        migrations.CreateModel(
            name="Caracteristica",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("categoria", models.CharField(max_length=120)),
                ("marca", models.CharField(max_length=120)),
                ("color", models.CharField(blank=True, max_length=80)),
                ("descripcion", models.TextField(blank=True)),
                ("precio_compra", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("precio_venta", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "caracteristica",
                "verbose_name_plural": "caracteristicas",
                "db_table": "caracteristicas_catalogo",
                "ordering": ["id"],
            },
        ),
    ]
