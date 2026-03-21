from datetime import datetime

from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from mensajeria.application.services import NotificacionService
from mensajeria.domain.entities import NotificacionEntidad
from mensajeria.infrastructure.repositories import NotificacionOrmRepository
from mensajeria.models import MensajeDirecto, MensajeEmpleado, Notificacion


@require_GET
@require_auth()
def listar_notificaciones(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    queryset = Notificacion.objects.order_by("-id")
    if usuario_id:
        queryset = queryset.filter(usuario_id=usuario_id)
    return success_response(
        {
            "items": [
                {
                    "id": notificacion.id,
                    "usuario_id": notificacion.usuario_id,
                    "titulo": notificacion.titulo,
                    "mensaje": notificacion.mensaje,
                    "tipo": notificacion.tipo,
                    "leida": notificacion.leida,
                    "fecha_creacion": notificacion.fecha_creacion.isoformat(),
                }
                for notificacion in queryset
            ]
        }
    )


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
    service = NotificacionService(NotificacionOrmRepository())
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
    queryset = MensajeDirecto.objects.order_by("-id")
    if usuario_id:
        queryset = queryset.filter(
            Q(destinatario_usuario_id=usuario_id) | Q(remitente_usuario_id=usuario_id)
        )
    return success_response(
        {
            "items": [
                {
                    "id": mensaje.id,
                    "conversacion_id": mensaje.conversacion_id,
                    "tipo_remitente": mensaje.tipo_remitente,
                    "remitente_usuario_id": mensaje.remitente_usuario_id,
                    "destinatario_usuario_id": mensaje.destinatario_usuario_id,
                    "asunto": mensaje.asunto,
                    "mensaje": mensaje.mensaje,
                    "estado": mensaje.estado,
                }
                for mensaje in queryset
            ]
        }
    )


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
        mensaje = MensajeDirecto.objects.create(
            conversacion_id=payload["conversacion_id"],
            mensaje_padre_id=payload.get("mensaje_padre_id"),
            tipo_remitente=payload["tipo_remitente"],
            remitente_usuario_id=remitente_objetivo_id,
            destinatario_usuario_id=payload.get("destinatario_usuario_id"),
            asunto=payload["asunto"],
            mensaje=payload["mensaje"],
            prioridad=payload.get("prioridad", "normal"),
            estado=payload.get("estado", "enviado"),
            empleado_asignado_id=payload.get("empleado_asignado_id"),
            respuesta=payload.get("respuesta", ""),
        )
    except KeyError as exc:
        return error_response(f"Campo requerido faltante: {exc}", status=400)
    return success_response({"id": mensaje.id}, status=201)


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_mensajes_empleado(request):
    empleado_id = request.GET.get("empleado_id")
    if request.usuario_actual.rol == "empleado":
        empleado_id = request.usuario_actual.id
    queryset = MensajeEmpleado.objects.order_by("-id")
    if empleado_id:
        queryset = queryset.filter(empleado_usuario_id=empleado_id)
    return success_response(
        {
            "items": [
                {
                    "id": mensaje.id,
                    "empleado_usuario_id": mensaje.empleado_usuario_id,
                    "remitente_usuario_id": mensaje.remitente_usuario_id,
                    "asunto": mensaje.asunto,
                    "tipo": mensaje.tipo,
                    "prioridad": mensaje.prioridad,
                    "leido": mensaje.leido,
                }
                for mensaje in queryset
            ]
        }
    )


@csrf_exempt
@require_POST
@require_auth(roles=["admin"])
def crear_mensaje_empleado(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    try:
        mensaje = MensajeEmpleado.objects.create(
            empleado_usuario_id=payload["empleado_usuario_id"],
            remitente_usuario_id=payload.get("remitente_usuario_id", request.usuario_actual.id),
            tipo_remitente=payload.get("tipo_remitente", "admin"),
            asunto=payload["asunto"],
            mensaje=payload["mensaje"],
            tipo=payload.get("tipo", "general"),
            prioridad=payload.get("prioridad", "normal"),
            leido=payload.get("leido", False),
            data_adicional=payload.get("data_adicional", {}),
        )
    except KeyError as exc:
        return error_response(f"Campo requerido faltante: {exc}", status=400)
    return success_response({"id": mensaje.id}, status=201)
