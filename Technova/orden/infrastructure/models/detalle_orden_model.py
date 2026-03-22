from django.db import models

from .orden_compra_model import OrdenCompra


class DetalleOrden(models.Model):
    orden_compra = models.ForeignKey(
        OrdenCompra,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "producto.Producto",
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
