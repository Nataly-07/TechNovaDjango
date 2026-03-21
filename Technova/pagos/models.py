from django.db import models


class Pago(models.Model):
    class EstadoPago(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"
        REEMBOLSADO = "reembolsado", "Reembolsado"

    fecha_pago = models.DateField()
    numero_factura = models.CharField(max_length=50, unique=True)
    fecha_factura = models.DateField()
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    estado_pago = models.CharField(
        max_length=20,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE,
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pagos"
        verbose_name = "pago"
        verbose_name_plural = "pagos"
        ordering = ["-fecha_pago", "-id"]


class MedioPago(models.Model):
    class Metodo(models.TextChoices):
        TARJETA_CREDITO = "tarjeta_credito", "Tarjeta de credito"
        TARJETA_DEBITO = "tarjeta_debito", "Tarjeta de debito"
        PSE = "pse", "PSE"
        TRANSFERENCIA = "transferencia", "Transferencia"
        EFECTIVO = "efectivo", "Efectivo"

    pago = models.ForeignKey(
        Pago,
        on_delete=models.PROTECT,
        related_name="medios_pago",
    )
    detalle_venta = models.ForeignKey(
        "ventas.DetalleVenta",
        on_delete=models.PROTECT,
        related_name="medios_pago",
    )
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.PROTECT,
        related_name="medios_pago",
    )
    metodo_pago = models.CharField(max_length=30, choices=Metodo.choices)
    fecha_compra = models.DateTimeField()
    tiempo_entrega = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "medios_pago"
        verbose_name = "medio de pago"
        verbose_name_plural = "medios de pago"
        ordering = ["-id"]


class MetodoPagoUsuario(models.Model):
    usuario = models.ForeignKey(
        "usuarios.Usuario",
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
