from functools import wraps

from common.api import error_response
from common.jwt_authentication import UsuarioJWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


def require_auth(roles=None):
    roles_permitidos = set(roles or [])
    authenticator = UsuarioJWTAuthentication()

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                auth_result = authenticator.authenticate(request)
            except (InvalidToken, TokenError):
                return error_response("Token invalido o expirado.", status=401)

            if auth_result is None:
                return error_response(
                    "No autenticado. Envia Authorization: Bearer <token>.",
                    status=401,
                )

            usuario, _ = auth_result

            if roles_permitidos and usuario.rol not in roles_permitidos:
                return error_response(
                    "No tienes permisos para esta operacion.",
                    status=403,
                )

            request.usuario_actual = usuario
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
