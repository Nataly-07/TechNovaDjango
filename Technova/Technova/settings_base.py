"""
Shared settings for all environments.
"""

from dotenv import load_dotenv

import os
from datetime import timedelta
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
# Cargar .env: junto a manage.py (Technova/.env) y, si faltan claves, raíz del repo (TechNovaDjango/.env).
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env", override=False)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "change-me-in-production-at-least-32-characters-long-secret",
)
DEBUG = _env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = _env_list("DJANGO_ALLOWED_HOSTS", ["127.0.0.1", "localhost"])

# CORS: lista separada por comas, p. ej. http://localhost:3000,https://app.example.com
_cors_origins_raw = os.getenv("DJANGO_CORS_ALLOWED_ORIGINS", "").strip()
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
CORS_ALLOW_CREDENTIALS = _env_bool("DJANGO_CORS_ALLOW_CREDENTIALS", False)

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.humanize",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "common.apps.CommonConfig",
    "web.apps.WebConfig",
    "usuario.apps.UsuarioConfig",
    "proveedor",
    "producto",
    "compra",
    "venta",
    "envio",
    "orden",
    "atencion_cliente",
    "mensajeria",
    "carrito",
    "pago",
    "correos",
    "channels",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "Technova.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context_processors.technova_frontend",
                "web.context_processors.technova_catalogo_nav",
            ],
        },
    },
]

WSGI_APPLICATION = "Technova.wsgi.application"
ASGI_APPLICATION = "Technova.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DB_NAME", "technova"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.getenv("DB_PASSWORD", "12345"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True
# Localización numérica (plantillas con {% localize %} / floatformat con separadores).
# Django 5+ ya no usa USE_L10N; el formateo local está activo con USE_I18N.
USE_THOUSAND_SEPARATOR = True
DECIMAL_SEPARATOR = ","
THOUSAND_SEPARATOR = "."
NUMBER_GROUPING = 3

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "common.jwt_authentication.UsuarioJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.drf_handlers.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Technova API",
    "DESCRIPTION": (
        "API REST Technova (JWT). La mayoría de rutas son vistas Django documentadas en "
        "`API_CONTRACTS.md`. Salud: `GET /api/v1/health/live/` y `/api/v1/health/ready/` "
        "(públicas). Esquema OpenAPI cubre sobre todo endpoints DRF; use el contrato "
        "Markdown como fuente de verdad para todas las rutas."
    ),
    "VERSION": "1.0.0",
    "AUTHENTICATION_WHITELIST": [],
    "SECURITY": [{"BearerAuth": []}],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
}

# PayPal Checkout (Sandbox)
TECHNOVA_PAYPAL_CLIENT_ID = os.getenv("TECHNOVA_PAYPAL_CLIENT_ID", "").strip()
TECHNOVA_PAYPAL_CLIENT_SECRET = os.getenv("TECHNOVA_PAYPAL_CLIENT_SECRET", "").strip()
TECHNOVA_PAYPAL_BASE_URL = os.getenv(
    "TECHNOVA_PAYPAL_BASE_URL",
    "https://api-m.sandbox.paypal.com",
).strip()
TECHNOVA_PAYPAL_CURRENCY = os.getenv("TECHNOVA_PAYPAL_CURRENCY", "USD").strip().upper()
# Admin: mostrar "PayPal" en lugar de "PSE" para medios guardados con el mapeo antiguo (paypal_sandbox → PSE).
# Pon TECHNOVA_ADMIN_PSE_LEGACY_COMO_PAYPAL=0 si tienes pagos PSE bancarios reales en "pse".
TECHNOVA_ADMIN_PSE_LEGACY_COMO_PAYPAL = _env_bool("TECHNOVA_ADMIN_PSE_LEGACY_COMO_PAYPAL", True)

# URL pública del sitio (enlaces absolutos en correos: confirmación de cuenta). Sin barra final.
TECHNOVA_PUBLIC_BASE_URL = os.getenv("TECHNOVA_PUBLIC_BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/")
# URL absoluta del logo en correos. Si TECHNOVA_EMAIL_LOGO_URL no está en el .env: ImgBB por defecto (estable en Gmail).
_logo_url_env = os.getenv("TECHNOVA_EMAIL_LOGO_URL")
if _logo_url_env is None:
    TECHNOVA_EMAIL_LOGO_URL = "https://i.ibb.co/tPZf30Tv/logo-TN.png"
else:
    TECHNOVA_EMAIL_LOGO_URL = _logo_url_env.strip()
# 0/false = solo URL en <img>. 1/true = incrustar Base64 en HTML si el código lo soporta (desactivado por defecto).
TECHNOVA_EMAIL_LOGO_EMBED_BASE64 = _env_bool("TECHNOVA_EMAIL_LOGO_EMBED_BASE64", False)

# Registro: False = envío sincrónico tras commit (más fiable; ver logs y errores SMTP al instante).
# True = hilo en segundo plano (no bloquea el POST; puede ocultar errores si no hay logging).
TECHNOVA_EMAIL_REGISTRO_ASYNC = _env_bool("TECHNOVA_EMAIL_REGISTRO_ASYNC", False)

# Correo (remitente y campañas masivas)
# Entrega a bandeja principal: usar SMTP de proveedor profesional (SendGrid, SES, Mailgun,
# Google Workspace) y variables de entorno para credenciales — no servidor local en producción.
# Reputación del dominio: configurar en DNS del dominio remitente registros SPF, DKIM y DMARC;
# sin ellos Gmail/Outlook suelen marcar o rechazar mensajes aunque el código sea correcto.
_default_from = os.getenv("DEFAULT_FROM_EMAIL", "").strip()
if not _default_from:
    _default_from = os.getenv("EMAIL_HOST_USER", "").strip() or "Technova <noreply@technova.local>"
DEFAULT_FROM_EMAIL = _default_from
# Visible en "Para:" en envíos masivos; los clientes van en BCC. Si la variable existe pero está vacía, To queda vacío.
_bulk_visible_raw = os.getenv("TECHNOVA_BULK_MAIL_VISIBLE_TO")
if _bulk_visible_raw is None:
    TECHNOVA_BULK_MAIL_VISIBLE_TO = DEFAULT_FROM_EMAIL
else:
    TECHNOVA_BULK_MAIL_VISIBLE_TO = _bulk_visible_raw.strip()
