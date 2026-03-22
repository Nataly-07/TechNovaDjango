from django.db import models


class Transportadora(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    telefono = models.CharField(max_length=20)
    correo_electronico = models.EmailField(unique=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transportadoras"
        verbose_name = "transportadora"
        verbose_name_plural = "transportadoras"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.nombre
