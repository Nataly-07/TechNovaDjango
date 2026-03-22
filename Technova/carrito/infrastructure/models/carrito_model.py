from django.db import models


class Carrito(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "activo", "Activo"
        CERRADO = "cerrado", "Cerrado"
        ABANDONADO = "abandonado", "Abandonado"

    usuario = models.ForeignKey(
        "usuario.Usuario",
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
