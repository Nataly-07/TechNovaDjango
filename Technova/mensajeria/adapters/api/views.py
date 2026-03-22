from datetime import datetime

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_mensajeria_query_service, get_notificacion_service
from mensajeria.domain.entities import NotificacionEntidad


@require_GET
@require_auth()
def listar_notificaciones(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    query_service = get_mensajeria_query_service()
    return success_response({"items": query_service.listar_notificaciones(usuario_id)})


@csrf_exempt
@require_POST
@require_auth()
def crear_notificacion(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    usuario_objetivo_id = payload.get("usuario_id", request.usuario_actual.id)
    if request.usuario_actual.rol != "admin" and usuario_objetivo_id != request.usuario_actual.id:
        return error_response("No puedes crear notificaciones para otro usuario.", status=403)

    notificacion = NotificacionEntidad(
        id=None,
        usuario_id=usuario_objetivo_id,
        titulo=payload["titulo"],
        mensaje=payload["mensaje"],
        tipo=payload.get("tipo", "general"),
        icono=payload.get("icono", "bell"),
        leida=payload.get("leida", False),
        fecha_creacion=datetime.fromisoformat(payload["fecha_creacion"])
        if payload.get("fecha_creacion")
        else datetime.now(),
    )
    service = get_notificacion_service()
    try:
        guardada = service.crear_notificacion(notificacion)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    return success_response({"id": guardada.id, "titulo": guardada.titulo}, status=201)


@require_GET
@require_auth()
def listar_mensajes_directos(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    query_service = get_mensajeria_query_service()
    return success_response({"items": query_service.listar_mensajes_directos(usuario_id)})


@csrf_exempt
@require_POST
@require_auth()
def crear_mensaje_directo(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    remitente_objetivo_id = payload.get("remitente_usuario_id", request.usuario_actual.id)
    if request.usuario_actual.rol != "admin" and remitente_objetivo_id != request.usuario_actual.id:
        return error_response("No puedes enviar mensajes como otro usuario.", status=403)

    try:
        mensaje_id = get_mensajeria_query_service().crear_mensaje_directo(
            {
                "conversacion_id": payload["conversacion_id"],
                "mensaje_padre_id": payload.get("mensaje_padre_id"),
                "tipo_remitente": payload["tipo_remitente"],
                "remitente_usuario_id": remitente_objetivo_id,
                "destinatario_usuario_id": payload.get("destinatario_usuario_id"),
                "asunto": payload["asunto"],
                "mensaje": payload["mensaje"],
                "prioridad": payload.get("prioridad", "normal"),
                "estado": payload.get("estado", "enviado"),
                "empleado_asignado_id": payload.get("empleado_asignado_id"),
                "respuesta": payload.get("respuesta", ""),
            }
        )
    except (KeyError, ValueError) as exc:
        return error_response(f"Campo requerido faltante: {exc}", status=400)
    return success_response({"id": mensaje_id}, status=201)


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_mensajes_empleado(request):
    empleado_id = request.GET.get("empleado_id")
    if request.usuario_actual.rol == "empleado":
        empleado_id = request.usuario_actual.id
    query_service = get_mensajeria_query_service()
    return success_response({"items": query_service.listar_mensajes_empleado(empleado_id)})


@csrf_exempt
@require_POST
@require_auth(roles=["admin"])
def crear_mensaje_empleado(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    try:
        mensaje_id = get_mensajeria_query_service().crear_mensaje_empleado(
            {
                "empleado_usuario_id": payload["empleado_usuario_id"],
                "remitente_usuario_id": payload.get("remitente_usuario_id", request.usuario_actual.id),
                "tipo_remitente": payload.get("tipo_remitente", "admin"),
                "asunto": payload["asunto"],
                "mensaje": payload["mensaje"],
                "tipo": payload.get("tipo", "general"),
                "prioridad": payload.get("prioridad", "normal"),
                "leido": payload.get("leido", False),
                "data_adicional": payload.get("data_adicional", {}),
            }
        )
    except (KeyError, ValueError) as exc:
        return error_response(f"Campo requerido faltante: {exc}", status=400)
    return success_response({"id": mensaje_id}, status=201)
