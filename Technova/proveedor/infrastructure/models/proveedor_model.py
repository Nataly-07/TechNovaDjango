from django.db import models


class Proveedor(models.Model):
    identificacion = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=120)
    telefono = models.CharField(max_length=20)
    correo_electronico = models.EmailField(unique=True)
    empresa = models.CharField(max_length=150, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "proveedores"
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.nombre
