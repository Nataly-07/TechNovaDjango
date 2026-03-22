from django.db import models

from .transportadora_model import Transportadora


class Envio(models.Model):
    class Estado(models.TextChoices):
        PREPARANDO = "preparando", "Preparando"
        EN_RUTA = "en_ruta", "En ruta"
        ENTREGADO = "entregado", "Entregado"
        DEVUELTO = "devuelto", "Devuelto"

    venta = models.ForeignKey(
        "venta.Venta",
        on_delete=models.PROTECT,
        related_name="envios",
    )
    transportadora = models.ForeignKey(
        Transportadora,
        on_delete=models.PROTECT,
        related_name="envios",
    )
    fecha_envio = models.DateTimeField()
    numero_guia = models.CharField(max_length=80, unique=True)
    costo_envio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PREPARANDO)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "envios"
        verbose_name = "envio"
        verbose_name_plural = "envios"
        ordering = ["-fecha_envio", "-id"]
