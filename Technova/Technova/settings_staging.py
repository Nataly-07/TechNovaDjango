from .settings_base import *  # noqa: F403,F401
from .settings_base import _env_list  # import * no incluye nombres con _

import os

DEBUG = False

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
