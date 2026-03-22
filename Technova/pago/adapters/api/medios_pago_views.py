from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_pago_query_service


@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_auth(roles=["admin", "empleado"])
def medios_pago_raiz(request):
    svc = get_pago_query_service()
    if request.method == "GET":
        return success_response({"items": svc.listar_medios_pago_lineas()})
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    try:
        creado = svc.crear_medio_pago_linea(payload)
    except Exception as exc:  # noqa: BLE001
        return error_response(str(exc), status=400)
    return success_response(creado, status=201)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
@require_auth(roles=["admin", "empleado"])
def medio_pago_por_id(request, medio_id: int):
    svc = get_pago_query_service()
    if request.method == "GET":
        data = svc.obtener_medio_pago_linea(medio_id)
        if data is None:
            return error_response("Medio de pago no encontrado.", status=404)
        return success_response(data)
    if request.method == "PUT":
        try:
            payload = parse_json_body(request)
        except ValueError as exc:
            return error_response(str(exc), status=400)
        data = svc.actualizar_medio_pago_linea(medio_id, payload)
        if data is None:
            return error_response("Medio de pago no encontrado.", status=404)
        return success_response(data)
    if not svc.desactivar_medio_pago_linea(medio_id):
        return error_response("Medio de pago no encontrado.", status=404)
    return success_response({}, message="Medio de pago desactivado")
