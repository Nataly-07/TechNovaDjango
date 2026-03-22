from django.db import models


class Notificacion(models.Model):
    usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.CASCADE,
        related_name="notificaciones",
    )
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    tipo = models.CharField(max_length=50)
    icono = models.CharField(max_length=80)
    leida = models.BooleanField(default=False)
    data_adicional = models.JSONField(default=dict, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notificaciones"
        verbose_name = "notificacion"
        verbose_name_plural = "notificaciones"
        ordering = ["-fecha_creacion", "-id"]
