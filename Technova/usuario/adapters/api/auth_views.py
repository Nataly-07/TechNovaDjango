from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from rest_framework_simplejwt.tokens import RefreshToken

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from usuario.application.use_cases.autenticacion_usecases import autenticar_por_correo
from usuario.models import Usuario


def _emitir_tokens(usuario: Usuario) -> tuple[str, str]:
    refresh = RefreshToken()
    refresh["usuario_id"] = usuario.id
    refresh["rol"] = usuario.rol
    refresh["correo"] = usuario.correo_electronico
    return str(refresh.access_token), str(refresh)


@csrf_exempt
@require_POST
def login(request):
    try:
        payload = parse_json_body(request)
        correo = payload["correo_electronico"].strip().lower()
        password = payload["contrasena"]
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)

    resultado = autenticar_por_correo(
        correo, password, tratar_inactivo_como_credenciales_invalidas=True
    )
    if resultado.usuario is None:
        return error_response("Credenciales invalidas.", status=401)

    usuario = resultado.usuario
    access, refresh = _emitir_tokens(usuario)
    return success_response(
        {
            "access": access,
            "refresh": refresh,
            "usuario": {
                "id": usuario.id,
                "correo_electronico": usuario.correo_electronico,
                "nombres": usuario.nombres,
                "apellidos": usuario.apellidos,
                "rol": usuario.rol,
            },
        },
        message="Login exitoso",
    )


@csrf_exempt
@require_POST
def refresh_token(request):
    try:
        payload = parse_json_body(request)
        refresh = RefreshToken(payload["refresh"])
    except Exception:
        return error_response("Refresh token invalido o expirado.", status=401)

    access = refresh.access_token
    return success_response({"access": str(access)}, message="Token renovado")


@require_GET
@require_auth()
def me(request):
    usuario = request.usuario_actual
    return success_response(
        {
            "id": usuario.id,
            "correo_electronico": usuario.correo_electronico,
            "nombres": usuario.nombres,
            "apellidos": usuario.apellidos,
            "rol": usuario.rol,
            "activo": usuario.activo,
        }
    )
