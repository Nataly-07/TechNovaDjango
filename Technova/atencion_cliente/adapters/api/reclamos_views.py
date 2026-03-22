from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_atencion_query_service


def _es_staff(usuario) -> bool:
    return usuario.rol in ("admin", "empleado")


def _puede_ver_reclamo(request, usuario_id_reclamo: int) -> bool:
    return _es_staff(request.usuario_actual) or request.usuario_actual.id == usuario_id_reclamo


@require_GET
@require_auth()
def listar_reclamos_usuario(request, usuario_id: int):
    if not _puede_ver_reclamo(request, usuario_id):
        return error_response("No tienes permisos.", status=403)
    items = get_atencion_query_service().listar_reclamos(usuario_id)
    return success_response({"items": items})


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_reclamos_estado(request, estado: str):
    items = get_atencion_query_service().listar_reclamos_por_estado(estado)
    return success_response({"items": items})


@csrf_exempt
@require_http_methods(["GET", "DELETE"])
@require_auth()
def detalle_o_eliminar_reclamo(request, reclamo_id: int):
    svc = get_atencion_query_service()
    if request.method == "GET":
        data = svc.reclamo_a_dict(reclamo_id)
        if data is None:
            return error_response("Reclamo no encontrado.", status=404)
        if not _puede_ver_reclamo(request, data["usuario_id"]):
            return error_response("No tienes permisos.", status=403)
        return success_response(data)
    row = svc.reclamo_a_dict(reclamo_id)
    if row is None:
        return error_response("Reclamo no encontrado.", status=404)
    if not (
        request.usuario_actual.rol == "admin"
        or row["usuario_id"] == request.usuario_actual.id
    ):
        return error_response("No tienes permisos.", status=403)
    if not svc.eliminar_reclamo(reclamo_id):
        return error_response("Reclamo no encontrado.", status=404)
    return success_response({}, message="Reclamo eliminado")


@csrf_exempt
@require_http_methods(["POST"])
@require_auth()
def crear_reclamo(request):
    usuario_id = request.POST.get("usuarioId") or request.POST.get("usuario_id")
    titulo = request.POST.get("titulo")
    descripcion = request.POST.get("descripcion")
    prioridad = request.POST.get("prioridad", "normal")
    if usuario_id is None:
        try:
            body = parse_json_body(request)
            usuario_id = body.get("usuarioId") or body.get("usuario_id")
            titulo = titulo or body.get("titulo")
            descripcion = descripcion or body.get("descripcion")
            prioridad = body.get("prioridad", prioridad)
        except ValueError:
            pass
    try:
        usuario_id = int(usuario_id)
    except (TypeError, ValueError):
        return error_response("usuarioId es requerido y debe ser entero.", status=400)
    if not titulo or not descripcion:
        return error_response("titulo y descripcion son requeridos.", status=400)
    if _es_staff(request.usuario_actual) is False and usuario_id != request.usuario_actual.id:
        return error_response("No puedes crear reclamos para otro usuario.", status=403)
    try:
        creado = get_atencion_query_service().crear_reclamo_basico(
            usuario_id, titulo, descripcion, prioridad
        )
    except Exception as exc:  # noqa: BLE001
        return error_response(str(exc), status=400)
    return success_response(creado, status=201)


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth(roles=["admin", "empleado"])
def responder_reclamo(request, reclamo_id: int):
    try:
        payload = parse_json_body(request)
        respuesta = payload.get("respuesta", "").strip()
    except ValueError as exc:
        return error_response(str(exc), status=400)
    if not respuesta:
        return error_response("La respuesta no puede estar vacia.", status=400)
    data = get_atencion_query_service().responder_reclamo(reclamo_id, respuesta)
    if data is None:
        return error_response("Reclamo no encontrado.", status=404)
    return success_response(data)


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth(roles=["admin", "empleado"])
def cerrar_reclamo(request, reclamo_id: int):
    data = get_atencion_query_service().cerrar_reclamo(reclamo_id)
    if data is None:
        return error_response("Reclamo no encontrado.", status=404)
    return success_response(data)


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth(roles=["admin", "empleado"])
def enviar_reclamo_admin(request, reclamo_id: int):
    data = get_atencion_query_service().enviar_reclamo_al_admin(reclamo_id)
    if data is None:
        return error_response("Reclamo no encontrado.", status=404)
    return success_response(data)


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth()
def evaluar_resolucion(request, reclamo_id: int):
    try:
        payload = parse_json_body(request)
        evaluacion = payload.get("evaluacion", "").strip()
    except ValueError as exc:
        return error_response(str(exc), status=400)
    if not evaluacion:
        return error_response("La evaluacion no puede estar vacia.", status=400)
    svc = get_atencion_query_service()
    row = svc.reclamo_a_dict(reclamo_id)
    if row is None:
        return error_response("Reclamo no encontrado.", status=404)
    if row["usuario_id"] != request.usuario_actual.id:
        return error_response("Solo el titular puede evaluar la resolucion.", status=403)
    data = svc.evaluar_resolucion_reclamo(reclamo_id, evaluacion)
    if data is None:
        return error_response("Reclamo no encontrado.", status=404)
    return success_response(data)
