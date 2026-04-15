"""
Envío de bienvenida + confirmación de correo (multipart HTML + texto plano).
El disparo desde el registro no debe bloquear la petición: usar hilo desde la señal.
"""

from __future__ import annotations

import logging
import threading
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import close_old_connections
from django.template.loader import render_to_string
from django.urls import reverse

from usuario.models import Usuario

logger = logging.getLogger(__name__)


def _ruta_logo_technova() -> Path | None:
    base = Path(settings.BASE_DIR)
    candidatos = [
        base / "static" / "frontend" / "imagenes" / "logo-technova.png",
    ]
    for p in candidatos:
        if p.is_file():
            return p
    return None


def _adjuntar_logo_inline(msg: EmailMultiAlternatives) -> None:
    logo_path = _ruta_logo_technova()
    if logo_path is None:
        return
    logo = MIMEImage(logo_path.read_bytes(), _subtype="png")
    logo.add_header("Content-ID", "<logo_technova>")
    logo.add_header("Content-Disposition", "inline")
    msg.attach(logo)


def _url_confirmacion(token: str) -> str:
    base = getattr(settings, "TECHNOVA_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not base:
        base = "http://127.0.0.1:8000"
    path = reverse("web_confirmar_correo", kwargs={"token": token})
    return f"{base}{path}"


def _cuerpo_texto_plano(nombre: str, tienda_url: str, confirmar_url: str) -> str:
    return (
        f"Hola {nombre},\n\n"
        "Gracias por crear tu cuenta en Technova.\n\n"
        "Para poder completar compras con tu cuenta, confirma tu correo con este enlace "
        f"(válido unos días):\n{confirmar_url}\n\n"
        f"Tienda: {tienda_url}\n\n"
        "Si no creaste esta cuenta, puedes ignorar este mensaje.\n\n"
        "— Technova\n"
    )


def enviar_bienvenida_y_confirmacion_correo(usuario_id: int) -> None:
    """
    Envía un solo correo con bienvenida y enlace de verificación.
    Pensado para ejecutarse en un hilo secundario (no bloquea el registro).
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
        token = (usuario.token_verificacion_correo or "").strip()
        if not token:
            logger.warning(
                "Correo registro: usuario_id=%s sin token de verificación en BD; no se envía mensaje.",
                usuario_id,
            )
            return

        logger.info(
            "Correo registro: enviando a %s (usuario_id=%s) con backend %s",
            correo,
            usuario_id,
            getattr(settings, "EMAIL_BACKEND", ""),
        )

        base = getattr(settings, "TECHNOVA_PUBLIC_BASE_URL", "").strip().rstrip("/")
        if not base:
            base = "http://127.0.0.1:8000"
        tienda_url = f"{base}/"
        confirmar_url = _url_confirmacion(token)

        asunto = "Bienvenida a Technova — confirma tu correo"
        html = render_to_string(
            "correos/email_bienvenida_verificacion.html",
            {
                "usuario": usuario,
                "nombre_usuario": usuario.nombres,
                "tienda_url": tienda_url,
                "confirmar_url": confirmar_url,
            },
        )
        texto = _cuerpo_texto_plano(usuario.nombres, tienda_url, confirmar_url)
        msg = EmailMultiAlternatives(
            subject=asunto,
            body=texto,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[correo],
        )
        msg.attach_alternative(html, "text/html")
        _adjuntar_logo_inline(msg)
        msg.send(fail_silently=False)
        logger.info("Correo registro: envío correcto para usuario_id=%s", usuario_id)
    except Exception:
        logger.exception(
            "Fallo al enviar correo de bienvenida/verificación (usuario_id=%s). "
            "Revisa SMTP (autenticación, puerto, firewall) o usa "
            "DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend para depurar.",
            usuario_id,
        )
    finally:
        close_old_connections()


def programar_envio_bienvenida_en_hilo(usuario_id: int) -> None:
    # daemon=False: el intérprete espera a que termine el envío al apagar (runserver recarga pueden seguir matando el hilo).
    t = threading.Thread(
        target=enviar_bienvenida_y_confirmacion_correo,
        args=(usuario_id,),
        daemon=False,
        name=f"technova-mail-{usuario_id}",
    )
    t.start()
