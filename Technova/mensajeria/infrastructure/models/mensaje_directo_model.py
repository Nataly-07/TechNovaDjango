from django.db import models


class MensajeDirecto(models.Model):
    class TipoRemitente(models.TextChoices):
        CLIENTE = "cliente", "Cliente"
        EMPLEADO = "empleado", "Empleado"

    class Prioridad(models.TextChoices):
        NORMAL = "normal", "Normal"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    class Estado(models.TextChoices):
        ENVIADO = "enviado", "Enviado"
        LEIDO = "leido", "Leido"
        RESPONDIDO = "respondido", "Respondido"

    conversacion_id = models.CharField(max_length=120, db_index=True)
    mensaje_padre = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="respuestas_hilo",
    )
    tipo_remitente = models.CharField(max_length=20, choices=TipoRemitente.choices)
    remitente_usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="mensajes_directos_enviados",
        null=True,
        blank=True,
    )
    destinatario_usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="mensajes_directos_recibidos",
        null=True,
        blank=True,
    )
    leido = models.BooleanField(default=False)
    leido_en = models.DateTimeField(null=True, blank=True)
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    prioridad = models.CharField(max_length=20, choices=Prioridad.choices, default=Prioridad.NORMAL)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ENVIADO)
    empleado_asignado = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.PROTECT,
        related_name="mensajes_directos_asignados",
        null=True,
        blank=True,
    )
    respuesta = models.TextField(blank=True)
    fecha_respuesta = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mensajes_directos"
        verbose_name = "mensaje directo"
        verbose_name_plural = "mensajes directos"
        ordering = ["-creado_en", "-id"]
