"""
Correo de bienvenida: HTML + texto plano mínimo, sin .attach() ni CID.

Logo: URL absoluta vía ``correos.email_logo.get_email_logo_src`` (env / sitio público).
"""

from __future__ import annotations

import logging
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import close_old_connections
from django.template.loader import render_to_string

from correos.email_logo import get_email_logo_src

from usuario.models import Usuario

logger = logging.getLogger(__name__)


def enviar_bienvenida_correo(usuario_id: int) -> None:
    """
    Un solo correo visual (template email_bienvenida.html).

    Usa EmailMultiAlternatives con alternativa HTML (sin .attach()).
    """
    close_old_connections()
    try:
        usuario = Usuario.objects.filter(pk=usuario_id).first()
        if usuario is None:
            logger.warning(
                "Correo registro: usuario_id=%s no existe; no se envía mensaje.",
                usuario_id,
            )
            return
        correo = (usuario.correo_electronico or "").strip()
        if not correo:
            logger.warning(
                "Correo registro: usuario_id=%s sin correo; no se envía mensaje.",
                usuario_id,
            )
            return

        base = getattr(settings, "TECHNOVA_PUBLIC_BASE_URL", "").strip().rstrip("/")
        if not base:
            base = "http://127.0.0.1:8000"
        tienda_url = f"{base}/"
        logo_src = get_email_logo_src()
        log_logo = (
            f"data:image/png;base64,<{len(logo_src)} chars>"
            if logo_src.startswith("data:")
            else logo_src
        )

        logger.info(
            "Correo registro: enviando a %s usuario_id=%s logo=%s backend=%s",
            correo,
            usuario_id,
            log_logo,
            getattr(settings, "EMAIL_BACKEND", ""),
        )

        asunto = "¡Bienvenido a Technova!"
        html = render_to_string(
            "correos/email_bienvenida.html",
            {
                "usuario": usuario,
                "nombre_usuario": usuario.nombres,
                "tienda_url": tienda_url,
                "logo_src": logo_src,
            },
        )
        texto_plano = (
            f"Hola {usuario.nombres},\n\n"
            "Bienvenido a Technova. Abre este mensaje en HTML para ver el diseño completo.\n\n"
            f"Tienda: {tienda_url}\n"
        )

        msg = EmailMultiAlternatives(
            subject=asunto,
            body=texto_plano,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[correo],
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
        logger.info("Correo registro: envío correcto usuario_id=%s", usuario_id)
    except Exception:
        logger.exception(
            "Fallo al enviar correo de bienvenida (usuario_id=%s). "
            "Comprueba SMTP y variables EMAIL_HOST_USER / EMAIL_HOST_PASSWORD en .env.",
            usuario_id,
        )
        raise
    finally:
        close_old_connections()


def programar_envio_bienvenida_en_hilo(usuario_id: int) -> None:
    t = threading.Thread(
        target=enviar_bienvenida_correo,
        args=(usuario_id,),
        daemon=False,
        name=f"technova-mail-{usuario_id}",
    )
    t.start()
