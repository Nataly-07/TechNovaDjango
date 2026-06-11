from .settings_base import *  # noqa: F403,F401
from .settings_base import _env_bool, _env_list  # import * no incluye nombres con _

import os

DEBUG = False

# Correo: sin credenciales SMTP → consola (evita 500 en registro en Railway).
_email_backend = os.getenv("DJANGO_EMAIL_BACKEND", "").strip()
if _email_backend:
    EMAIL_BACKEND = _email_backend
elif os.getenv("EMAIL_HOST_USER", "").strip() and os.getenv("EMAIL_HOST_PASSWORD", "").strip():
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com").strip()
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").strip()

if not os.environ.get("DEFAULT_FROM_EMAIL", "").strip() and EMAIL_HOST_USER:
    DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
if os.environ.get("TECHNOVA_BULK_MAIL_VISIBLE_TO") is None and EMAIL_HOST_USER:
    TECHNOVA_BULK_MAIL_VISIBLE_TO = DEFAULT_FROM_EMAIL

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

# Railway / hosting: dominio público y CSRF
CSRF_TRUSTED_ORIGINS = _env_list("DJANGO_CSRF_TRUSTED_ORIGINS", [])
_railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
if _railway_domain:
    _railway_origin = f"https://{_railway_domain}"
    if _railway_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_railway_origin)
    if _railway_domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_railway_domain)

if not os.getenv("TECHNOVA_PUBLIC_BASE_URL", "").strip() and _railway_domain:
    TECHNOVA_PUBLIC_BASE_URL = f"https://{_railway_domain}"
