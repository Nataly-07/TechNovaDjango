"""Contexto global para plantillas del frontend (misma base que el proyecto Java + API Django)."""

from web.session_cliente import compra_tienda_bloqueada_por_perfil_gestion, sesion_es_cliente


def technova_frontend(_request):
    return {
        "TECHNOVA_API_PREFIX": "/api/v1",
    }


def technova_catalogo_nav(_request):
    """Categorías y marcas para nav / filtros en index e inicio cliente."""
    from web.catalogo_nav import listas_categorias_marcas_publicas

    cats, marcas = listas_categorias_marcas_publicas()
    return {"categorias": cats, "marcas": marcas}


def technova_cliente_flags(request):
    """UI tienda: favoritos solo Cliente; compra bloqueada para Admin/Empleado."""
    bloqueada, etiqueta = compra_tienda_bloqueada_por_perfil_gestion(request)
    return {
        "mostrar_favoritos": sesion_es_cliente(request),
        "compra_bloqueada_perfil_gestion": bloqueada,
        "rol_compra_bloqueada_etiqueta": etiqueta,
    }
