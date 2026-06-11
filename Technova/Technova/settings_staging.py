from .settings_base import *  # noqa: F403,F401
from .settings_base import _env_list  # import * no incluye nombres con _

import os

DEBUG = False

# --- Correo en producción (Railway): Resend por API HTTPS ---
# SMTP (Gmail:587) está bloqueado en Railway Hobby; usar RESEND_API_KEY.
_resend_api_key = os.getenv("RESEND_API_KEY", "").strip()
_email_backend_override = os.getenv("DJANGO_EMAIL_BACKEND", "").strip()

if _email_backend_override:
    EMAIL_BACKEND = _email_backend_override
elif _resend_api_key:
    INSTALLED_APPS = [*INSTALLED_APPS, "anymail"]
    EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
    ANYMAIL = {"RESEND_API_KEY": _resend_api_key}
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

if _resend_api_key and not os.environ.get("DEFAULT_FROM_EMAIL", "").strip():
    DEFAULT_FROM_EMAIL = os.getenv(
        "RESEND_FROM_EMAIL",
        "Technova <onboarding@resend.dev>",
    ).strip()

# Registro web: no bloquear el POST mientras se llama a la API de Resend.
if os.getenv("TECHNOVA_EMAIL_REGISTRO_ASYNC", "").strip() == "":
    TECHNOVA_EMAIL_REGISTRO_ASYNC = True

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
