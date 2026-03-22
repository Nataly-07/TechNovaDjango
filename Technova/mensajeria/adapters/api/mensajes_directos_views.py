from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_mensajeria_query_service
from mensajeria.models import MensajeDirecto


def _staff(u) -> bool:
    return u.rol in ("admin", "empleado")


def _puede_ver_mensaje(request, data: dict) -> bool:
    if _staff(request.usuario_actual):
        return True
    uid = request.usuario_actual.id
    return data.get("senderId") == uid or data.get("receiverId") == uid


def _puede_ver_conversacion(request, conversacion_id: str) -> bool:
    if _staff(request.usuario_actual):
        return True
    uid = request.usuario_actual.id
    return MensajeDirecto.objects.filter(conversacion_id=conversacion_id).filter(
        Q(remitente_usuario_id=uid) | Q(destinatario_usuario_id=uid)
    ).exists()


@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_auth()
def mensajes_directos_raiz(request):
    svc = get_mensajeria_query_service()
    if request.method == "GET":
        if not _staff(request.usuario_actual):
            return error_response("No tienes permisos.", status=403)
        return success_response({"items": svc.listar_mensajes_directos_todos()})
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    remitente = payload.get("remitente_usuario_id", request.usuario_actual.id)
    if not _staff(request.usuario_actual) and remitente != request.usuario_actual.id:
        return error_response("No puedes enviar como otro usuario.", status=403)
    try:
        mid = svc.crear_mensaje_directo(
            {
                "conversacion_id": payload["conversacion_id"],
                "mensaje_padre_id": payload.get("mensaje_padre_id"),
                "tipo_remitente": payload["tipo_remitente"],
                "remitente_usuario_id": remitente,
                "destinatario_usuario_id": payload.get("destinatario_usuario_id"),
                "asunto": payload["asunto"],
                "mensaje": payload["mensaje"],
                "prioridad": payload.get("prioridad", "normal"),
                "estado": payload.get("estado", "enviado"),
                "empleado_asignado_id": payload.get("empleado_asignado_id"),
                "respuesta": payload.get("respuesta", ""),
            }
        )
    except (KeyError, TypeError, ValueError) as exc:
        return error_response(str(exc), status=400)
    data = svc.obtener_mensaje_directo(mid)
    return success_response(data, status=201)


@require_GET
@require_auth()
def mensajes_por_usuario(request, user_id: int):
    if not _staff(request.usuario_actual) and user_id != request.usuario_actual.id:
        return error_response("No tienes permisos.", status=403)
    items = get_mensajeria_query_service().listar_mensajes_directos(user_id)
    return success_response({"items": items})


@require_GET
@require_auth()
def mensajes_por_empleado(request, empleado_id: int):
    if not _staff(request.usuario_actual):
        return error_response("No tienes permisos.", status=403)
    if request.usuario_actual.rol == "empleado" and empleado_id != request.usuario_actual.id:
        return error_response("No tienes permisos.", status=403)
    items = get_mensajeria_query_service().listar_mensajes_por_empleado(empleado_id)
    return success_response({"items": items})


@require_GET
@require_auth()
def mensajes_por_conversacion(request, conversation_id: str):
    if not _puede_ver_conversacion(request, conversation_id):
        return error_response("No tienes permisos.", status=403)
    items = get_mensajeria_query_service().listar_mensajes_por_conversacion(conversation_id)
    return success_response({"items": items})


@csrf_exempt
@require_http_methods(["POST"])
@require_auth()
def crear_conversacion(request):
    user_id = request.POST.get("userId")
    asunto = request.POST.get("asunto")
    mensaje = request.POST.get("mensaje")
    prioridad = request.POST.get("prioridad", "normal")
    if user_id is None:
        try:
            body = parse_json_body(request)
            user_id = body.get("userId")
            asunto = asunto or body.get("asunto")
            mensaje = mensaje or body.get("mensaje")
            prioridad = body.get("prioridad", prioridad)
        except ValueError:
            pass
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return error_response("userId requerido.", status=400)
    if not asunto or not mensaje:
        return error_response("asunto y mensaje son requeridos.", status=400)
    if not _staff(request.usuario_actual) and user_id != request.usuario_actual.id:
        return error_response("No tienes permisos.", status=403)
    try:
        data = get_mensajeria_query_service().crear_conversacion_inicial(
            user_id, asunto, mensaje, prioridad
        )
    except Exception as exc:  # noqa: BLE001
        return error_response(str(exc), status=400)
    return success_response(data, status=201)


@require_GET
@require_auth()
def detalle_mensaje_directo(request, mensaje_id: int):
    svc = get_mensajeria_query_service()
    data = svc.obtener_mensaje_directo(mensaje_id)
    if data is None:
        return error_response("Mensaje no encontrado.", status=404)
    if not _puede_ver_mensaje(request, data):
        return error_response("No tienes permisos.", status=403)
    return success_response(data)


@csrf_exempt
@require_http_methods(["POST"])
@require_auth()
def responder_mensaje_directo(request, mensaje_id: int):
    sender_id = request.POST.get("senderId")
    sender_type = request.POST.get("senderType")
    mensaje = request.POST.get("mensaje")
    if sender_id is None:
        try:
            body = parse_json_body(request)
            sender_id = body.get("senderId")
            sender_type = body.get("senderType")
            mensaje = body.get("mensaje")
        except ValueError:
            pass
    try:
        sender_id = int(sender_id)
    except (TypeError, ValueError):
        return error_response("senderId invalido.", status=400)
    if not sender_type or not mensaje:
        return error_response("senderType y mensaje son requeridos.", status=400)
    if not _staff(request.usuario_actual) and sender_id != request.usuario_actual.id:
        return error_response("No tienes permisos.", status=403)
    try:
        data = get_mensajeria_query_service().responder_mensaje_directo(
            mensaje_id, sender_id, sender_type, mensaje
        )
    except ValueError as exc:
        return error_response(str(exc), status=400)
    if data is None:
        return error_response("Mensaje no encontrado.", status=404)
    return success_response(data)


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth()
def marcar_leido_mensaje(request, mensaje_id: int):
    svc = get_mensajeria_query_service()
    prev = svc.obtener_mensaje_directo(mensaje_id)
    if prev is None:
        return error_response("Mensaje no encontrado.", status=404)
    if not _puede_ver_mensaje(request, prev):
        return error_response("No tienes permisos.", status=403)
    data = svc.marcar_mensaje_leido(mensaje_id)
    return success_response(data)


@require_GET
@require_auth(roles=["admin", "empleado"])
def estadisticas_mensajes_directos(request):
    return success_response(get_mensajeria_query_service().estadisticas_mensajes_directos())
