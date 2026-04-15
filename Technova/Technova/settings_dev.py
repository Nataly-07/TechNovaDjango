import os
import warnings

from .settings_base import *  # noqa: F403,F401


DEBUG = True

# Backend de correo: prioridad DJANGO_EMAIL_BACKEND > modo consola de depuración > SMTP.
_email_backend = os.getenv("DJANGO_EMAIL_BACKEND", "").strip()
if _email_backend:
    EMAIL_BACKEND = _email_backend
elif os.getenv("DJANGO_EMAIL_CONSOLE", "").strip().lower() in {"1", "true", "yes", "on"}:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com").strip()
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "1").strip().lower() in {"1", "true", "yes", "on"}
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").strip()

if not os.environ.get("DEFAULT_FROM_EMAIL", "").strip():
    if EMAIL_HOST_USER:
        DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
if os.environ.get("TECHNOVA_BULK_MAIL_VISIBLE_TO") is None and EMAIL_HOST_USER:
    TECHNOVA_BULK_MAIL_VISIBLE_TO = DEFAULT_FROM_EMAIL

if "smtp" in EMAIL_BACKEND.lower() and not (EMAIL_HOST_USER and EMAIL_HOST_PASSWORD):
    warnings.warn(
        "Correo: SMTP activo pero EMAIL_HOST_USER o EMAIL_HOST_PASSWORD están vacíos. "
        "Revisa Technova/.env o la raíz del repo; define credenciales o usa "
        "DJANGO_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend para ver el mensaje en consola.",
        stacklevel=1,
    )

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "usuario": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
