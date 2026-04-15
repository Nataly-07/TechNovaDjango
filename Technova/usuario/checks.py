"""Comprobaciones de configuración de correo al arrancar (runserver / check)."""

from django.conf import settings
from django.core.checks import Warning, register


@register()
def email_smtp_credenciales(app_configs, **kwargs):
    errores = []
    backend = (getattr(settings, "EMAIL_BACKEND", "") or "").lower()
    if "smtp" not in backend:
        return errores
    user = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
    password = (getattr(settings, "EMAIL_HOST_PASSWORD", "") or "").strip()
    if not user or not password:
        errores.append(
            Warning(
                "SMTP activo pero faltan EMAIL_HOST_USER o EMAIL_HOST_PASSWORD. "
                "Coloca el .env en Technova/ o en la raíz del repositorio, o prueba con "
                "DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend.",
                id="technova.mail.W001",
            )
        )
    return errores
