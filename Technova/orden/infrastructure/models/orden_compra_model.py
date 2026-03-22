from django.db import models


class OrdenCompra(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        RECIBIDA = "recibida", "Recibida"
        CANCELADA = "cancelada", "Cancelada"

    proveedor = models.ForeignKey(
        "proveedor.Proveedor",
        on_delete=models.PROTECT,
        related_name="ordenes_compra",
    )
    fecha = models.DateField()
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ordenes_compra"
        verbose_name = "orden de compra"
        verbose_name_plural = "ordenes de compra"
        ordering = ["-fecha", "-id"]
