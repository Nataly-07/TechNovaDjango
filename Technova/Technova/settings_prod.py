import os

from .settings_base import _env_bool
from .settings_staging import *  # noqa: F403,F401

# Railway (y la mayoría de PaaS) terminan TLS en el proxy. El healthcheck interno
# llama por HTTP sin X-Forwarded-Proto → SECURE_SSL_REDIRECT devolvía 301 y fallaba el deploy.
SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Respaldo si en otro host se activa SECURE_SSL_REDIRECT vía variable de entorno.
SECURE_REDIRECT_EXEMPT = [
    r"^/api/v1/health/live/?$",
    r"^/api/v1/health/ready/?$",
    r"^/api/health/live/?$",
    r"^/api/health/ready/?$",
]
