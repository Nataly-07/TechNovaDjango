from functools import wraps

from django.shortcuts import redirect

from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.infrastructure.models.usuario_model import Usuario


def cliente_login_required(view_func):
    """Solo usuarios con sesión Django (misma clave que login_web)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get(SESSION_USUARIO_ID):
            return redirect("web_login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_login_required(view_func):
    """Sesión activa y rol administrador."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        print(f"🔍 DEBUG: Sesión completa: {dict(request.session)}")
        uid = request.session.get(SESSION_USUARIO_ID)
        print(f"🔍 DEBUG: UID extraído: {uid}")
        if not uid:
            print("🔍 DEBUG: No hay UID, redirigiendo a login")
            return redirect("web_login")
        try:
            print(f"🔍 DEBUG: Buscando usuario con pk={uid}")
            usuario = Usuario.objects.get(pk=uid)
            print(f"🔍 DEBUG: Usuario encontrado: {usuario}, rol: {usuario.rol}")
        except Usuario.DoesNotExist:
            print("🔍 DEBUG: Usuario no existe, limpiando sesión y redirigiendo")
            request.session.flush()
            return redirect("web_login")
        if usuario.rol != Usuario.Rol.ADMIN:
            print(f"🔍 DEBUG: Usuario no es admin ({usuario.rol}), redirigiendo a inicio")
            return redirect("inicio_autenticado")
        print(f"🔍 DEBUG: Usuario admin válido, ejecutando vista")
        return view_func(request, *args, **kwargs)

    return _wrapped


def empleado_login_required(view_func):
    """Sesión activa y rol empleado (panel propio; admin y cliente redirigen)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        uid = request.session.get(SESSION_USUARIO_ID)
        if not uid:
            return redirect("web_login")
        try:
            usuario = Usuario.objects.get(pk=uid)
        except Usuario.DoesNotExist:
            request.session.flush()
            return redirect("web_login")
        if usuario.rol == Usuario.Rol.ADMIN:
            return redirect("web_admin_perfil")
        if usuario.rol != Usuario.Rol.EMPLEADO:
            return redirect("inicio_autenticado")
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_o_empleado_login_required(view_func):
    """Administrador o empleado autenticado (p. ej. recepción de órdenes de compra)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        uid = request.session.get(SESSION_USUARIO_ID)
        if not uid:
            return redirect("web_login")
        try:
            usuario = Usuario.objects.get(pk=uid)
        except Usuario.DoesNotExist:
            request.session.flush()
            return redirect("web_login")
        if usuario.rol not in (Usuario.Rol.ADMIN, Usuario.Rol.EMPLEADO):
            return redirect("inicio_autenticado")
        request.usuario_sesion = usuario  # type: ignore[attr-defined]
        return view_func(request, *args, **kwargs)

    return _wrapped
