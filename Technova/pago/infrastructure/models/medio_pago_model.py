from django.db import models

from .pago_model import Pago


class MedioPago(models.Model):
    class Metodo(models.TextChoices):
        TARJETA_CREDITO = "tarjeta_credito", "Tarjeta de credito"
        TARJETA_DEBITO = "tarjeta_debito", "Tarjeta de debito"
        PSE = "pse", "PSE"
        TRANSFERENCIA = "transferencia", "Transferencia"
        EFECTIVO = "efectivo", "Efectivo"

    pago = models.ForeignKey(
        Pago,
        on_delete=models.PROTECT,
        related_name="medios_pago",
    )
    detalle_venta = models.ForeignKey(
        "venta.DetalleVenta",
        on_delete=models.PROTECT,
        related_name="medios_pago",
    )
    usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="medios_pago",
    )
    metodo_pago = models.CharField(max_length=30, choices=Metodo.choices)
    fecha_compra = models.DateTimeField()
    tiempo_entrega = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "medios_pago"
        verbose_name = "medio de pago"
        verbose_name_plural = "medios de pago"
        ordering = ["-id"]
