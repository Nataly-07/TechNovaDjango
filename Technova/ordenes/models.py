from django.db import models


class OrdenCompra(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        RECIBIDA = "recibida", "Recibida"
        CANCELADA = "cancelada", "Cancelada"

    proveedor = models.ForeignKey(
        "proveedores.Proveedor",
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


class DetalleOrden(models.Model):
    orden_compra = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        related_name="detalles_orden_compra",
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = "detalle_ordenes_compra"
        verbose_name = "detalle de orden de compra"
        verbose_name_plural = "detalles de orden de compra"
