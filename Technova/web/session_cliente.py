"""Sesión web y rol Cliente (compras / favoritos personales)."""

from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.infrastructure.models.usuario_model import Usuario


def sesion_es_cliente(request) -> bool:
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return False
    try:
        return Usuario.objects.only("rol").get(pk=uid).rol == Usuario.Rol.CLIENTE
    except Usuario.DoesNotExist:
        return False


def compra_tienda_bloqueada_por_perfil_gestion(request) -> tuple[bool, str]:
    """
    Administrador y Empleado no compran en la tienda (solo gestión).
    Devuelve (True, etiqueta rol) si la compra debe bloquearse; si no aplica, (False, "").
    """
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return False, ""
    try:
        u = Usuario.objects.only("rol").get(pk=uid)
    except Usuario.DoesNotExist:
        return False, ""
    if u.rol == Usuario.Rol.ADMIN:
        return True, Usuario.Rol.ADMIN.label
    if u.rol == Usuario.Rol.EMPLEADO:
        return True, Usuario.Rol.EMPLEADO.label
    return False, ""
