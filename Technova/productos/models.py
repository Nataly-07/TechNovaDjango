from django.db import models


class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=120)
    imagen_url = models.URLField(blank=True)
    stock = models.PositiveIntegerField(default=0)
    proveedor = models.ForeignKey(
        "proveedores.Proveedor",
        on_delete=models.PROTECT,
        related_name="productos",
    )
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "productos"
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"
