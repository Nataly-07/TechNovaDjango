from django.db import models


class Usuario(models.Model):
    class Rol(models.TextChoices):
        ADMIN = "admin", "Administrador"
        CLIENTE = "cliente", "Cliente"
        EMPLEADO = "empleado", "Empleado"

    nombre_usuario = models.CharField(max_length=120, unique=True)
    correo_electronico = models.EmailField(unique=True)
    contrasena_hash = models.CharField(max_length=255)
    nombres = models.CharField(max_length=120)
    apellidos = models.CharField(max_length=120)
    tipo_documento = models.CharField(max_length=30)
    numero_documento = models.CharField(max_length=40, unique=True)
    telefono = models.CharField(max_length=20)
    direccion = models.TextField()
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.CLIENTE)
    activo = models.BooleanField(default=True)
    correo_verificado = models.BooleanField(default=True)
    token_verificacion_correo = models.CharField(max_length=128, blank=True, default="")
    token_verificacion_expira = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "usuarios"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.nombres} {self.apellidos}".strip()
