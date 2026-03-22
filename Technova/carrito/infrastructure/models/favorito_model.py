from django.db import models


class Favorito(models.Model):
    usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.CASCADE,
        related_name="favoritos",
    )
    producto = models.ForeignKey(
        "producto.Producto",
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
