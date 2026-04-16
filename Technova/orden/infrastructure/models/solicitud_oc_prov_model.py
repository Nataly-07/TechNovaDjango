from django.db import models


class SolicitudOrdenCompraProv(models.Model):
    """
    Solicitud de reabastecimiento creada por empleado; el admin la aprueba y genera OrdenCompra.
    """

    class Estado(models.TextChoices):
        BORRADOR = "borrador", "En edición"
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    empleado = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.CASCADE,
        related_name="solicitudes_oc_prov",
    )
    producto = models.ForeignKey(
        "producto.Producto",
        on_delete=models.PROTECT,
        related_name="solicitudes_oc_prov",
    )
    proveedor = models.ForeignKey(
        "proveedor.Proveedor",
        on_delete=models.PROTECT,
        related_name="solicitudes_oc_prov",
    )
    cantidad = models.PositiveIntegerField()
    cantidad_aprobada = models.PositiveIntegerField(null=True, blank=True)
    comentario_empleado = models.TextField(blank=True, default="")
    motivo_rechazo = models.TextField(blank=True, default="")
    marca_snapshot = models.CharField(max_length=120, blank=True, default="")
    color_snapshot = models.CharField(max_length=40, blank=True, default="")
    costo_unitario_snapshot = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
    )
    orden_compra = models.ForeignKey(
        "orden.OrdenCompra",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="solicitudes_origen",
    )
    enviada_en = models.DateTimeField(null=True, blank=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "solicitudes_oc_prov"
        verbose_name = "solicitud orden compra prov"
        verbose_name_plural = "solicitudes órdenes compra prov"
        ordering = ["-creado_en", "-id"]

    def __str__(self) -> str:
        return f"Solicitud #{self.pk} — {self.get_estado_display()}"
