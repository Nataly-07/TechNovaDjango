from .settings_base import *  # noqa: F403,F401


DEBUG = True


# Configuración de correo para entorno de desarrollo
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'technovaprueba@gmail.com'  #  Gmail real
EMAIL_HOST_PASSWORD = 'penjdgtgjhmvqjsn'  # contraseña de aplicación