from django.db import models


class Venta(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        FACTURADA = "facturada", "Facturada"
        ANULADA = "anulada", "Anulada"

    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="ventas",
    )
    fecha_venta = models.DateField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ventas"
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-fecha_venta", "-id"]


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        related_name="detalles_venta",
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "detalle_ventas"
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"
