from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage
from pathlib import Path
import logging

from usuario.infrastructure.models.usuario_model import Usuario

logger = logging.getLogger(__name__)


def _adjuntar_logo_cid(msg: EmailMultiAlternatives) -> None:
    """
    Adjunta logo inline por CID para entorno local.
    """
    candidatos = [
        Path(
            "C:/Users/Marcela/.cursor/projects/d-Nataly-DjangoVI-TechNovaDjango/assets/"
            "c__Users_Marcela_AppData_Roaming_Cursor_User_workspaceStorage_6fe0e0b928196acd4af263defd0b8f41_images_"
            "image-f2ee58ae-53aa-485a-9edd-3ef89852adfe.png"
        ),
        Path(
            "C:/Users/Marcela/.cursor/projects/d-Nataly-DjangoVI-TechNovaDjango/assets/"
            "c__Users_Marcela_AppData_Roaming_Cursor_User_workspaceStorage_6fe0e0b928196acd4af263defd0b8f41_images_"
            "image-56fb4712-af6f-4358-9bdb-fc0b62b35529.png"
        ),
        Path(
            "C:/Users/Marcela/.cursor/projects/d-Nataly-DjangoVI-TechNovaDjango/assets/"
            "c__Users_Marcela_AppData_Roaming_Cursor_User_workspaceStorage_6fe0e0b928196acd4af263defd0b8f41_images_"
            "image-fb336cc0-7a1c-4878-aeb6-9fc5a2941b48.png"
        ),
    ]
    logo_path = next((p for p in candidatos if p.exists()), None)
    if logo_path is None:
        return
    logo = MIMEImage(logo_path.read_bytes(), _subtype="png")
    logo.add_header("Content-ID", "<logo_technova>")
    logo.add_header("Content-Disposition", "inline")
    msg.attach(logo)


@receiver(post_save, sender=Usuario)
def enviar_bienvenida_usuario(sender, instance, created, **kwargs):
    """
    Signal para enviar correo de bienvenida automáticamente
    cuando se crea un nuevo usuario
    """
    if not created:
        return  # Solo para nuevos usuarios
    
    try:
        # En el modelo `Usuario` el campo de correo se llama `correo_electronico`
        # (en este proyecto no existe `instance.email`).
        correo = getattr(instance, "correo_electronico", None) or getattr(instance, "email", None)
        if not correo:
            raise AttributeError("No se encontró el correo del usuario (correo_electronico/email).")

        tienda_url = getattr(settings, "TECHNOVA_PUBLIC_URL", "").strip() or "http://127.0.0.1:8000/"
        contexto = {
            'usuario': instance,
            'nombre_usuario': instance.nombres,
            'tienda_url': tienda_url,
        }
        
        mensaje_html = render_to_string('correos/email_bienvenida.html', contexto)
        
        asunto = f'¡Bienvenido a Technova, {instance.nombres}!'
        
        msg = EmailMultiAlternatives(
            subject=asunto,
            body='Bienvenido a Technova. Tu cuenta fue creada con éxito.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[correo],
        )
        msg.attach_alternative(mensaje_html, "text/html")
        _adjuntar_logo_cid(msg)
        msg.send(fail_silently=False)
        
        logger.info(f"Correo de bienvenida enviado a {correo}")
        
    except Exception as e:
        # No lanzamos la excepción para no interrumpir el registro del usuario
        logger.error(f"Error al enviar correo de bienvenida: {e}")
        # No lanzamos la excepción para no interrumpir el registro del usuario


@receiver(post_save, sender=Usuario)
def registrar_historial_bienvenida(sender, instance, created, **kwargs):
    """
    Registrar en el historial el envío de bienvenida
    """
    if not created:
        return
    
    try:
        correo = getattr(instance, "correo_electronico", None) or getattr(instance, "email", None)
        if not correo:
            raise AttributeError("No se encontró el correo del usuario (correo_electronico/email).")

        from .models import HistorialEnvio, DestinatarioEnvio
        
        # Crear historial de envío de bienvenida
        historial = HistorialEnvio.objects.create(
            asunto=f'Bienvenida - {instance.nombres}',
            cuerpo_mensaje='Correo de bienvenida automático',
            total_destinatarios=1,
            tipo_envio='bienvenida',
            autor=None,  # Es automático
            estado='completado',
            enviados_exitosos=1,
            enviados_fallidos=0
        )
        
        # Crear registro de destinatario
        DestinatarioEnvio.objects.create(
            historial=historial,
            destinatario=instance,
            email=correo,
            estado='enviado'
        )
        
    except Exception as e:
        logger.error(f"Error al registrar historial de bienvenida: {e}")
        # No lanzamos la excepción para no interrumpir el registro
