"""Contexto global para plantillas del frontend (misma base que el proyecto Java + API Django)."""


def technova_frontend(_request):
    return {
        "TECHNOVA_API_PREFIX": "/api/v1",
    }


def technova_catalogo_nav(_request):
    """Categorías y marcas para nav / filtros en index e inicio cliente."""
    from web.catalogo_nav import listas_categorias_marcas_publicas

    cats, marcas = listas_categorias_marcas_publicas()
    return {"categorias": cats, "marcas": marcas}
