from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_pago_query_service


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_todos_metodos_usuario(request):
    items = get_pago_query_service().listar_metodos_usuario(None)
    return success_response({"items": items})


@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_auth()
def metodos_usuario(request, usuario_id: int):
    if request.usuario_actual.rol != "admin" and usuario_id != request.usuario_actual.id:
        return error_response("No tienes permisos.", status=403)
    svc = get_pago_query_service()
    if request.method == "GET":
        items = svc.listar_metodos_usuario(usuario_id)
        return success_response({"items": items})
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    try:
        mid = svc.crear_metodo_usuario(
            {
                "usuario_id": usuario_id,
                "metodo_pago": payload["metodo_pago"],
                "es_predeterminado": payload.get("es_predeterminado", False),
                "marca": payload.get("marca", ""),
                "ultimos_cuatro": payload.get("ultimos_cuatro", ""),
                "nombre_titular": payload.get("nombre_titular", ""),
                "token": payload.get("token", ""),
                "mes_expiracion": payload.get("mes_expiracion", ""),
                "anio_expiracion": payload.get("anio_expiracion", ""),
                "correo": payload.get("correo", ""),
                "telefono": payload.get("telefono", ""),
                "cuotas": payload.get("cuotas"),
            }
        )
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    return success_response({"id": mid}, status=201)
