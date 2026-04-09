from django.db import models


class Venta(models.Model):
    class TipoVenta(models.TextChoices):
        ONLINE = "online", "Online"
        FISICA = "fisica", "Física"

    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        FACTURADA = "facturada", "Facturada"
        ANULADA = "anulada", "Anulada"

    usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="ventas",
    )
    tipo_venta = models.CharField(
        max_length=10,
        choices=TipoVenta.choices,
        default=TipoVenta.ONLINE,
    )
    empleado = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="ventas_fisicas_realizadas",
        null=True,
        blank=True,
    )
    administrador = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="ventas_registradas_como_admin",
        null=True,
        blank=True,
    )
    fecha_venta = models.DateField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    datos_facturacion_mostrador = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Datos de facturación (mostrador, sin cuenta)",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ventas"
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ["-fecha_venta", "-id"]
