import os

from .settings_base import *  # noqa: F403,F401


DEBUG = True


# Configuración de correo para entorno de desarrollo
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'technovaprueba@gmail.com'  #  Gmail real
EMAIL_HOST_PASSWORD = 'penjdgtgjhmvqjsn'  # contraseña de aplicación

# Si no vienen por .env, usar la misma cuenta SMTP como remitente y "Para:" visible en campañas (BCC a clientes).
if not os.environ.get("DEFAULT_FROM_EMAIL", "").strip():
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
if os.environ.get("TECHNOVA_BULK_MAIL_VISIBLE_TO") is None:
    TECHNOVA_BULK_MAIL_VISIBLE_TO = DEFAULT_FROM_EMAIL