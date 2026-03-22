from django.db import models

from .carrito_model import Carrito


class DetalleCarrito(models.Model):
    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "producto.Producto",
        on_delete=models.PROTECT,
        related_name="detalles_carrito",
    )
    cantidad = models.PositiveIntegerField(default=1)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "detalle_carritos"
        verbose_name = "detalle de carrito"
        verbose_name_plural = "detalles de carrito"
        constraints = [
            models.UniqueConstraint(
                fields=["carrito", "producto"],
                name="uq_detalle_carrito_producto",
            )
        ]
