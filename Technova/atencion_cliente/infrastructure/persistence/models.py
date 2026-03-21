from django.db import models


class AtencionCliente(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        EN_PROCESO = "en_proceso", "En proceso"
        CERRADA = "cerrada", "Cerrada"

    usuario = models.ForeignKey(
        "usuarios.Usuario",
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


class Reclamo(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_REVISION = "en_revision", "En revision"
        RESUELTO = "resuelto", "Resuelto"
        CERRADO = "cerrado", "Cerrado"

    class Prioridad(models.TextChoices):
        BAJA = "baja", "Baja"
        NORMAL = "normal", "Normal"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    class EvaluacionCliente(models.TextChoices):
        RESUELTA = "resuelta", "Resuelta"
        NO_RESUELTA = "no_resuelta", "No resuelta"

    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="reclamos",
    )
    fecha_reclamo = models.DateTimeField()
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    respuesta = models.TextField(blank=True)
    prioridad = models.CharField(max_length=20, choices=Prioridad.choices, default=Prioridad.NORMAL)
    enviado_al_admin = models.BooleanField(default=False)
    evaluacion_cliente = models.CharField(
        max_length=20,
        choices=EvaluacionCliente.choices,
        blank=True,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reclamos"
        verbose_name = "reclamo"
        verbose_name_plural = "reclamos"
        ordering = ["-fecha_reclamo", "-id"]
