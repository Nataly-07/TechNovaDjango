from django.db import models
from django.contrib.auth.models import User
from usuario.infrastructure.models.usuario_model import Usuario


class HistorialEnvio(models.Model):
    """Modelo para auditar envíos de correos masivos"""
    
    TIPO_ENVIO_CHOICES = [
        ('promocion', 'Promoción de Producto'),
        ('campana', 'Campaña Manual'),
        ('bienvenida', 'Bienvenida Automática'),
        ('notificacion', 'Notificación General'),
    ]
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviando', 'Enviando'),
        ('completado', 'Completado'),
        ('error', 'Error'),
        ('parcial', 'Parcial (algunos fallaron)'),
    ]
    
    asunto = models.CharField(max_length=200, verbose_name="Asunto")
    cuerpo_mensaje = models.TextField(verbose_name="Mensaje")
    fecha_envio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Envío")
    total_destinatarios = models.PositiveIntegerField(default=0, verbose_name="Total Destinatarios")
    enviados_exitosos = models.PositiveIntegerField(default=0, verbose_name="Enviados Exitosos")
    enviados_fallidos = models.PositiveIntegerField(default=0, verbose_name="Enviados Fallidos")
    tipo_envio = models.CharField(max_length=20, choices=TIPO_ENVIO_CHOICES, default='campana', verbose_name="Tipo de Envío")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name="Estado")
    
    # Autor del envío (Admin que lo realizó)
    autor = models.ForeignKey(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Autor",
        related_name="envios_realizados"
    )
    
    # Referencia opcional a producto (para promociones)
    producto = models.ForeignKey(
        'producto.Producto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Producto Promocionado"
    )
    
    # Datos adicionales para auditoría
    ip_origen = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP de Origen")
    user_agent = models.TextField(null=True, blank=True, verbose_name="User Agent")
    
    class Meta:
        verbose_name = "Historial de Envío"
        verbose_name_plural = "Historiales de Envíos"
        ordering = ['-fecha_envio']
        
    def __str__(self):
        return f"{self.asunto} - {self.fecha_envio.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def tasa_exito(self):
        """Calcular tasa de éxito en porcentaje"""
        if self.total_destinatarios == 0:
            return 0
        return round((self.enviados_exitosos / self.total_destinatarios) * 100, 2)


class DestinatarioEnvio(models.Model):
    """Modelo para registrar cada destinatario individual de un envío"""
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviado', 'Enviado'),
        ('fallido', 'Fallido'),
        ('rebotado', 'Rebotado'),
    ]
    
    historial = models.ForeignKey(
        HistorialEnvio,
        on_delete=models.CASCADE,
        related_name="destinatarios",
        verbose_name="Historial de Envío"
    )
    
    destinatario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        verbose_name="Destinatario"
    )
    
    email = models.EmailField(verbose_name="Email del Destinatario")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name="Estado")
    fecha_envio = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Envío")
    error_message = models.TextField(null=True, blank=True, verbose_name="Mensaje de Error")
    
    class Meta:
        verbose_name = "Destinatario de Envío"
        verbose_name_plural = "Destinatarios de Envíos"
        unique_together = ['historial', 'destinatario']
