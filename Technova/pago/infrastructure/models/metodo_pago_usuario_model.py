from django.db import models


class MetodoPagoUsuario(models.Model):
    usuario = models.ForeignKey(
        "usuario.Usuario",
        on_delete=models.CASCADE,
        related_name="metodos_pago_usuario",
    )
    metodo_pago = models.CharField(max_length=30)
    es_predeterminado = models.BooleanField(default=False)
    marca = models.CharField(max_length=50, blank=True)
    ultimos_cuatro = models.CharField(max_length=4, blank=True)
    nombre_titular = models.CharField(max_length=150, blank=True)
    token = models.CharField(max_length=255, blank=True)
    mes_expiracion = models.CharField(max_length=2, blank=True)
    anio_expiracion = models.CharField(max_length=4, blank=True)
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    cuotas = models.PositiveIntegerField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "metodos_pago_usuario"
        verbose_name = "metodo de pago de usuario"
        verbose_name_plural = "metodos de pago de usuario"
        ordering = ["-id"]
