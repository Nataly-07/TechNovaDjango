"""
Logo TechNova en correos HTML: URL absoluta (recomendado para Gmail / Outlook).

Prioridad (ver ``settings.TECHNOVA_EMAIL_LOGO_URL``):
1. Valor de ``TECHNOVA_EMAIL_LOGO_URL`` en el .env (puede ser vacío ``""``).
2. Si la variable no está en el .env: URL por defecto (ImgBB) en ``settings_base``.
3. Si en el .env la dejaste explícitamente vacía: ``{TECHNOVA_PUBLIC_BASE_URL}/static/.../logo-technova-email.png`` (PNG 3× para nitidez al mostrarlo pequeño).
"""

from __future__ import annotations

from django.conf import settings

STATIC_LOGO_PATH = "/static/frontend/imagenes/logo-technova-email.png"


def get_email_logo_src() -> str:
    explicit = (getattr(settings, "TECHNOVA_EMAIL_LOGO_URL", "") or "").strip()
    if explicit:
        return explicit
    base = (getattr(settings, "TECHNOVA_PUBLIC_BASE_URL", "") or "").strip().rstrip("/")
    if not base:
        base = "http://127.0.0.1:8000"
    return f"{base}{STATIC_LOGO_PATH}"
