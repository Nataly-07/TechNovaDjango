from django.db import models


class Caracteristica(models.Model):
    categoria = models.CharField(max_length=120)
    marca = models.CharField(max_length=120)
    color = models.CharField(max_length=80, blank=True)
    descripcion = models.TextField(blank=True)
    precio_compra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "caracteristicas_catalogo"
        verbose_name = "caracteristica"
        verbose_name_plural = "caracteristicas"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.marca} {self.categoria}"
