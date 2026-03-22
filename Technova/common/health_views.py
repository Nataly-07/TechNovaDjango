"""Endpoints públicos de salud para balanceadores y monitoreo."""

from django.db import connection
from django.views.decorators.http import require_GET

from common.api import error_response, success_response


@require_GET
def health_live(_request):
    """Liveness: el proceso responde (sin comprobar dependencias)."""
    return success_response({"live": True}, message="ok")


@require_GET
def health_ready(_request):
    """Readiness: comprobación mínima de base de datos."""
    try:
        connection.ensure_connection()
    except Exception as exc:  # noqa: BLE001
        return error_response(f"Base de datos no disponible: {exc}", status=503)
    return success_response({"ready": True, "database": "ok"}, message="ok")
