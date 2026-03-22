"""Contexto global para plantillas del frontend (misma base que el proyecto Java + API Django)."""


def technova_frontend(_request):
    return {
        "TECHNOVA_API_PREFIX": "/api/v1",
    }
