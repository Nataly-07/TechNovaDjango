from django.db import models
from django.utils import timezone


class OrdenCompra(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        RECIBIDA = "recibida", "Recibida"
        COMPLETADA = "completada", "Completada"
        CANCELADA = "cancelada", "Cancelada"

    proveedor = models.ForeignKey(
        "proveedor.Proveedor",
        on_delete=models.PROTECT,
        related_name="ordenes_compra",
    )
    fecha = models.DateField()
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones_recepcion = models.TextField(blank=True, default="")
    recepcion_validada_en = models.DateTimeField(null=True, blank=True)
    recepcion_validada_por = models.ForeignKey(
        "usuario.Usuario",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ordenes_compra_recepciones_validadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ordenes_compra"
        verbose_name = "orden de compra"
        verbose_name_plural = "ordenes de compra"
        ordering = ["-fecha", "-id"]

    def texto_resumen_recepcion_inventario(self) -> str:
        """Mensaje de historial tras validar recepción (inventario)."""
        if not self.recepcion_validada_en:
            return ""
        u = self.recepcion_validada_por
        nombre = (
            f"{u.nombres} {u.apellidos}".strip()
            if u
            else "Usuario del sistema"
        )
        dt = timezone.localtime(self.recepcion_validada_en)
        return (
            f"Pedido validado y cargado al inventario por {nombre} "
            f"el {dt.strftime('%d/%m/%Y')} a las {dt.strftime('%H:%M')}."
        )

    def __str__(self) -> str:
        return f"Orden #{self.pk} — {self.get_estado_display()}"
