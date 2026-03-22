from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_envio_query_service


@require_GET
@require_auth(roles=["admin", "empleado"])
def transportadoras_por_envio(request, envio_id: int):
    items = get_envio_query_service().listar_transportadoras_por_envio(envio_id)
    return success_response({"items": items})


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
@require_auth(roles=["admin", "empleado"])
def transportadora_por_id(request, transportadora_id: int):
    svc = get_envio_query_service()
    if request.method == "GET":
        data = svc.obtener_transportadora(transportadora_id)
        if data is None:
            return error_response("Transportadora no encontrada.", status=404)
        return success_response(data)
    if request.method == "PUT":
        try:
            payload = parse_json_body(request)
        except ValueError as exc:
            return error_response(str(exc), status=400)
        data = svc.actualizar_transportadora(transportadora_id, payload)
        if data is None:
            return error_response("Transportadora no encontrada.", status=404)
        return success_response(data)
    if not svc.desactivar_transportadora(transportadora_id):
        return error_response("Transportadora no encontrada.", status=404)
    return success_response({}, message="Transportadora desactivada")


@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_auth(roles=["admin", "empleado"])
def transportadoras_raiz(request):
    svc = get_envio_query_service()
    if request.method == "GET":
        return success_response({"items": svc.listar_transportadoras()})
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    tid = svc.crear_transportadora(
        {
            "nombre": payload["nombre"],
            "telefono": payload["telefono"],
            "correo_electronico": payload.get("correo_electronico") or payload.get("correo"),
            "activo": payload.get("activo", True),
        }
    )
    data = svc.obtener_transportadora(tid)
    return success_response(data, status=201)
