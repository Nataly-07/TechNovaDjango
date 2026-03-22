"""
API REST de usuarios (/api/usuario/).
Formato de usuario en data: campos estilo UsuarioDto (firstName, email, role, estado, ...).
"""

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.jwt_authentication import UsuarioJWTAuthentication
from usuario.application.registro_usuario_service import (
    mensaje_integridad_registro,
    registrar_usuario_desde_payload,
    validar_contrasena_politica,
)
from usuario.application.use_cases.autenticacion_usecases import autenticar_por_correo
from usuario.models import Usuario


def _emitir_tokens(usuario: Usuario) -> tuple[str, str]:
    refresh = RefreshToken()
    refresh["usuario_id"] = usuario.id
    refresh["rol"] = usuario.rol
    refresh["correo"] = usuario.correo_electronico
    return str(refresh.access_token), str(refresh)


def _payload_str(payload: dict, *keys: str, default: str | None = None) -> str | None:
    for k in keys:
        if k in payload and payload[k] is not None and str(payload[k]).strip() != "":
            return str(payload[k]).strip()
    return default


def usuario_a_dto(usuario: Usuario) -> dict:
    return {
        "id": usuario.id,
        "name": usuario.nombre_usuario,
        "email": usuario.correo_electronico,
        "firstName": usuario.nombres,
        "lastName": usuario.apellidos,
        "documentType": usuario.tipo_documento,
        "documentNumber": usuario.numero_documento,
        "phone": usuario.telefono,
        "address": usuario.direccion,
        "role": usuario.rol,
        "estado": usuario.activo,
    }


def _usuario_optional_admin(request):
    """Si hay Bearer valido y rol admin, devuelve el usuario; si no, None."""
    authenticator = UsuarioJWTAuthentication()
    try:
        auth_result = authenticator.authenticate(request)
    except (InvalidToken, TokenError):
        return None
    if auth_result is None:
        return None
    usuario, _ = auth_result
    return usuario if usuario.rol == "admin" else None


def _rol_valido(val: str) -> bool:
    return val in {c[0] for c in Usuario.Rol.choices}


@csrf_exempt
@require_http_methods(["GET", "POST"])
def catalogo_usuarios(request):
    if request.method == "GET":
        return require_auth(roles=["admin", "empleado"])(_listar_usuarios)(request)
    return _registrar_usuario(request)


def _listar_usuarios(request):
    items = [usuario_a_dto(u) for u in Usuario.objects.order_by("id")]
    return success_response({"items": items, "usuarios": items})


def _registrar_usuario(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    admin = _usuario_optional_admin(request)
    result = registrar_usuario_desde_payload(payload, admin_usuario=admin)
    if result.error:
        return error_response(result.error, status=400)
    return success_response(usuario_a_dto(result.usuario), message="Usuario creado", status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def usuario_por_id(request, usuario_id: int):
    if request.method == "GET":
        return require_auth()(_detalle_usuario)(request, usuario_id)
    if request.method == "PUT":
        return require_auth()(_actualizar_usuario)(request, usuario_id)
    return require_auth(roles=["admin"])(_eliminar_usuario)(request, usuario_id)


def _puede_ver_o_editar(request, usuario_id: int) -> bool:
    u = request.usuario_actual
    return u.rol in ("admin", "empleado") or u.id == usuario_id


def _detalle_usuario(request, usuario_id: int):
    if not _puede_ver_o_editar(request, usuario_id):
        return error_response("No tienes permisos para ver este usuario.", status=403)
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        return error_response("Usuario no encontrado.", status=404)
    return success_response(usuario_a_dto(usuario))


def _actualizar_usuario(request, usuario_id: int):
    if not _puede_ver_o_editar(request, usuario_id):
        return error_response("No tienes permisos para editar este usuario.", status=403)
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        return error_response("Usuario no encontrado.", status=404)

    puede_cambiar_rol = request.usuario_actual.rol == "admin"

    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    nu = _payload_str(payload, "name", "nombre_usuario")
    if nu:
        if Usuario.objects.filter(nombre_usuario=nu).exclude(id=usuario.id).exists():
            return error_response("El nombre de usuario ya esta en uso.", status=400)
        usuario.nombre_usuario = nu

    em = _payload_str(payload, "email", "correo_electronico", "correo")
    if em:
        em = em.lower()
        if Usuario.objects.filter(correo_electronico=em).exclude(id=usuario.id).exists():
            return error_response("El correo ya esta registrado.", status=400)
        usuario.correo_electronico = em

    fn = _payload_str(payload, "firstName", "nombres")
    if fn:
        usuario.nombres = fn
    ln = _payload_str(payload, "lastName", "apellidos")
    if ln:
        usuario.apellidos = ln
    dt = _payload_str(payload, "documentType", "tipo_documento")
    if dt:
        usuario.tipo_documento = dt
    dn = _payload_str(payload, "documentNumber", "numero_documento")
    if dn:
        if Usuario.objects.filter(numero_documento=dn).exclude(id=usuario.id).exists():
            return error_response("El documento ya esta registrado.", status=400)
        usuario.numero_documento = dn
    ph = _payload_str(payload, "phone", "telefono")
    if ph:
        usuario.telefono = ph
    ad = _payload_str(payload, "address", "direccion")
    if ad is not None:
        usuario.direccion = ad

    pwd = _payload_str(payload, "password", "contrasena")
    if pwd:
        err = validar_contrasena_politica(pwd)
        if err:
            return error_response(err, status=400)
        usuario.contrasena_hash = make_password(pwd)

    if puede_cambiar_rol:
        raw_rol = (_payload_str(payload, "role", "rol") or "").lower()
        if raw_rol and _rol_valido(raw_rol):
            usuario.rol = raw_rol

    if "estado" in payload and puede_cambiar_rol:
        usuario.activo = bool(payload["estado"])

    try:
        usuario.save()
    except IntegrityError:
        return error_response(mensaje_integridad_registro(), status=400)

    return success_response(usuario_a_dto(usuario))


def _eliminar_usuario(request, usuario_id: int):
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        return error_response("Usuario no encontrado.", status=404)
    usuario.activo = False
    usuario.save(update_fields=["activo", "actualizado_en"])
    return success_response({}, message="Usuario desactivado", status=200)


@csrf_exempt
@require_http_methods(["PATCH"])
@require_auth(roles=["admin"])
def patch_estado_usuario(request, usuario_id: int):
    activar_s = request.GET.get("activar")
    if activar_s is None:
        try:
            body = parse_json_body(request)
            activar_s = body.get("activar")
        except ValueError:
            activar_s = None
    if activar_s is None:
        return error_response("Parametro activar requerido.", status=400)
    activar = str(activar_s).lower() in ("1", "true", "yes", "on")
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        return error_response("Usuario no encontrado.", status=404)
    usuario.activo = activar
    usuario.save(update_fields=["activo", "actualizado_en"])
    return success_response({}, message="Estado actualizado")


@csrf_exempt
@require_POST
def verificar_identidad(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return success_response({"valid": False, "message": str(exc)}, status=200)

    email = _payload_str(payload, "email", "correo_electronico")
    doc_type = _payload_str(payload, "documentType", "tipo_documento")
    doc_num = _payload_str(payload, "documentNumber", "numero_documento")
    phone = _payload_str(payload, "phone", "telefono")

    if not all([email, doc_type, doc_num, phone]):
        return success_response(
            {"valid": False, "message": "Todos los campos son requeridos"},
            status=200,
        )

    ok = Usuario.objects.filter(
        correo_electronico__iexact=email.strip().lower(),
        tipo_documento=doc_type,
        numero_documento=doc_num,
        telefono=phone,
    ).exists()
    data = {"valid": ok}
    if not ok:
        data["message"] = "Los datos no coinciden con nuestros registros"
    return success_response(data)


@csrf_exempt
@require_POST
def recuperar_contrasena(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return success_response({"success": False, "message": str(exc)}, status=200)

    email = _payload_str(payload, "email", "correo_electronico")
    new_password = _payload_str(payload, "newPassword", "nueva_contrasena", "contrasena")

    if not email or not new_password:
        return success_response(
            {"success": False, "message": "Email y nueva contrasena son requeridos"},
            status=200,
        )

    err = validar_contrasena_politica(new_password)
    if err:
        return success_response({"success": False, "message": err}, status=200)

    try:
        usuario = Usuario.objects.get(correo_electronico__iexact=email.lower())
    except Usuario.DoesNotExist:
        return success_response(
            {
                "success": False,
                "message": "No se pudo actualizar la contrasena. Verifica que el email sea correcto.",
            },
            status=200,
        )

    usuario.contrasena_hash = make_password(new_password)
    usuario.save(update_fields=["contrasena_hash", "actualizado_en"])
    return success_response({"success": True, "message": "Contrasena actualizada correctamente"})


@csrf_exempt
@require_POST
def activar_cuenta(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return success_response({"success": False, "message": str(exc)}, status=200)

    email = _payload_str(payload, "email", "correo_electronico")
    if not email:
        return success_response({"success": False, "message": "Email es requerido"}, status=200)

    try:
        usuario = Usuario.objects.get(correo_electronico__iexact=email.lower())
    except Usuario.DoesNotExist:
        return success_response({"success": False, "message": "Usuario no encontrado"}, status=200)

    usuario.activo = True
    usuario.save(update_fields=["activo", "actualizado_en"])
    return success_response({"success": True, "message": "Cuenta activada correctamente"})


@csrf_exempt
@require_POST
def usuarios_login_compat(request):
    """POST /api/usuario/login/ con email/password (o equivalentes en español). Incluye JWT para el front Django."""
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    email = (_payload_str(payload, "email", "correo_electronico") or "").lower()
    password = _payload_str(payload, "password", "contrasena")
    if not email or not password:
        return error_response("Credenciales invalidas.", status=401)

    resultado = autenticar_por_correo(
        email, password, tratar_inactivo_como_credenciales_invalidas=False
    )
    if resultado.error == "inactivo":
        return error_response("Cuenta inactiva.", status=401)
    if resultado.usuario is None:
        return error_response("Credenciales invalidas.", status=401)

    usuario = resultado.usuario
    access, refresh = _emitir_tokens(usuario)
    return success_response(
        {
            **usuario_a_dto(usuario),
            "access": access,
            "refresh": refresh,
        },
        message="Login exitoso",
    )


@require_GET
def verificar_estado(request):
    email = request.GET.get("email") or request.GET.get("correo")
    if not email:
        return error_response("Parametro email requerido.", status=400)
    usuario = Usuario.objects.filter(correo_electronico__iexact=email.strip().lower()).first()
    if usuario:
        return success_response({"exists": True, "active": usuario.activo})
    return success_response({"exists": False, "active": False})
