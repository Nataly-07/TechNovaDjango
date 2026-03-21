from django.db import models


class Carrito(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        CERRADO = "cerrado", "Cerrado"
        ABANDONADO = "abandonado", "Abandonado"

    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="carritos",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)

    class Meta:
        db_table = "carritos"
        verbose_name = "carrito"
        verbose_name_plural = "carritos"
        ordering = ["-fecha_creacion", "-id"]


class DetalleCarrito(models.Model):
    carrito = models.ForeignKey(
        Carrito,
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "productos.Producto",
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


class Favorito(models.Model):
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="favoritos",
    )
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.CASCADE,
        related_name="favoritos",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "favoritos"
        verbose_name = "favorito"
        verbose_name_plural = "favoritos"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "producto"],
                name="uq_favorito_usuario_producto",
            )
        ]
