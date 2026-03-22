from django.db import models


class AtencionCliente(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        EN_PROCESO = "en_proceso", "En proceso"
        CERRADA = "cerrada", "Cerrada"

    usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="solicitudes_atencion",
    )
    fecha_consulta = models.DateTimeField()
    tema = models.CharField(max_length=150)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    respuesta = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "atencion_cliente"
        verbose_name = "atencion al cliente"
        verbose_name_plural = "atencion al cliente"
        ordering = ["-fecha_consulta", "-id"]
