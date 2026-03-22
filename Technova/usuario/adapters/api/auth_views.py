from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from rest_framework_simplejwt.tokens import RefreshToken

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from usuario.models import Usuario


def _credenciales_validas(password_plano: str, valor_guardado: str) -> bool:
    if not valor_guardado:
        return False

    # Soporta hashes Django y contrasenas legacy en texto plano.
    if valor_guardado.startswith(("pbkdf2_", "argon2$", "bcrypt$", "scrypt$")):
        return check_password(password_plano, valor_guardado)
    return password_plano == valor_guardado


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

    try:
        usuario = Usuario.objects.get(correo_electronico=correo, activo=True)
    except Usuario.DoesNotExist:
        return error_response("Credenciales invalidas.", status=401)

    if not _credenciales_validas(password, usuario.contrasena_hash):
        return error_response("Credenciales invalidas.", status=401)

    # Migra de texto plano a hash de Django en el primer login exitoso.
    if not usuario.contrasena_hash.startswith(("pbkdf2_", "argon2$", "bcrypt$", "scrypt$")):
        usuario.contrasena_hash = make_password(password)
        usuario.save(update_fields=["contrasena_hash", "actualizado_en"])

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
