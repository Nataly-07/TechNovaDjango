from django.db import models


class ProductoCatalogoExtra(models.Model):
    """Marcas y categorías extra definidas por el admin (además de las predeterminadas)."""

    class Tipo(models.TextChoices):
        CATEGORIA = "categoria", "Categoría"
        MARCA = "marca", "Marca"

    tipo = models.CharField(max_length=20, choices=Tipo.choices, db_index=True)
    nombre = models.CharField(max_length=120)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "productos_catalogo_extra"
        constraints = [
            models.UniqueConstraint(fields=["tipo", "nombre"], name="uniq_catalogo_extra_tipo_nombre"),
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()}: {self.nombre}"
