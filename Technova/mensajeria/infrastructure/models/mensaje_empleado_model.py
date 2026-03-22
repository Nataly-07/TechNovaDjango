from django.db import models


class MensajeEmpleado(models.Model):
    class TipoRemitente(models.TextChoices):
        ADMIN = "admin", "Administrador"
        SISTEMA = "sistema", "Sistema"
        EMPLEADO = "empleado", "Empleado"

    class Prioridad(models.TextChoices):
        NORMAL = "normal", "Normal"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    empleado_usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="mensajes_empleado_recibidos",
    )
    remitente_usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="mensajes_empleado_enviados",
    )
    tipo_remitente = models.CharField(max_length=20, choices=TipoRemitente.choices)
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=50)
    prioridad = models.CharField(max_length=20, choices=Prioridad.choices, default=Prioridad.NORMAL)
    leido = models.BooleanField(default=False)
    fecha_leido = models.DateTimeField(null=True, blank=True)
    data_adicional = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mensajes_empleado"
        verbose_name = "mensaje a empleado"
        verbose_name_plural = "mensajes a empleados"
        ordering = ["-creado_en", "-id"]
