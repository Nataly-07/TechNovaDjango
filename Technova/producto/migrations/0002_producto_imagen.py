# Generated migration for producto_imagen

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('producto', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductoImagen',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(max_length=500, verbose_name='url')),
                ('orden', models.PositiveIntegerField(default=0, verbose_name='orden')),
                ('activa', models.BooleanField(default=True, verbose_name='activa')),
                ('creado_en', models.DateTimeField(auto_now_add=True, verbose_name='creado en')),
                ('producto', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='imagenes', to='producto.producto', verbose_name='producto')),
            ],
            options={
                'verbose_name': 'imagen de producto',
                'verbose_name_plural': 'imágenes de productos',
                'db_table': 'producto_imagenes',
                'ordering': ['orden', 'id'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='productoimagen',
            unique_together=[('producto', 'orden')],
        ),
    ]
