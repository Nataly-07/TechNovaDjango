from django.db import models


class Compra(models.Model):
    class Estado(models.TextChoices):
        REGISTRADA = "registrada", "Registrada"
        PAGADA = "pagada", "Pagada"
        ANULADA = "anulada", "Anulada"

    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="compras",
    )
    proveedor = models.ForeignKey(
        "proveedores.Proveedor",
        on_delete=models.PROTECT,
        related_name="compras",
    )
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.REGISTRADA,
    )
    fecha_compra = models.DateTimeField()
    tiempo_entrega_estimado = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "compras"
        verbose_name = "compra"
        verbose_name_plural = "compras"
        ordering = ["-fecha_compra", "-id"]


class DetalleCompra(models.Model):
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        related_name="detalles_compra",
    )
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "detalle_compras"
        verbose_name = "detalle de compra"
        verbose_name_plural = "detalles de compra"
