from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_mensajeria_query_service, get_notificacion_service
from mensajeria.domain.entities import NotificacionEntidad


@csrf_exempt
@require_http_methods(["GET", "POST"])
@require_auth(roles=["admin", "empleado"])
def notificaciones_raiz(request):
    if request.method == "GET":
        items = get_mensajeria_query_service().listar_notificaciones_todas()
        return success_response({"items": items})
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    uid = payload.get("userId") or payload.get("usuario_id")
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        return error_response("userId requerido.", status=400)
    fc_raw = payload.get("fechaCreacion") or payload.get("fecha_creacion")
    if fc_raw:
        try:
            fc = datetime.fromisoformat(str(fc_raw).replace("Z", "+00:00"))
        except ValueError:
            fc = timezone.now()
    else:
        fc = timezone.now()
    if timezone.is_naive(fc):
        fc = timezone.make_aware(fc, timezone.get_current_timezone())
    entidad = NotificacionEntidad(
        id=None,
        usuario_id=uid,
        titulo=payload.get("titulo", ""),
        mensaje=payload.get("mensaje", ""),
        tipo=payload.get("tipo", "general"),
        icono=payload.get("icono", "bell"),
        leida=payload.get("leida", False),
        fecha_creacion=fc,
    )
    try:
        guardada = get_notificacion_service().crear_notificacion(entidad)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    return success_response(
        {
            "id": guardada.id,
            "userId": guardada.usuario_id,
            "titulo": guardada.titulo,
            "mensaje": guardada.mensaje,
            "tipo": guardada.tipo,
            "leida": guardada.leida,
        },
        status=201,
    )


@require_GET
@require_auth()
def notificaciones_por_usuario(request, user_id: int):
    if request.usuario_actual.rol != "admin" and user_id != request.usuario_actual.id:
        return error_response("No tienes permisos.", status=403)
    solo = request.GET.get("soloNoLeidas", "false").lower() in ("1", "true", "yes")
    items = get_mensajeria_query_service().listar_notificaciones_filtradas(
        user_id, solo_no_leidas=solo
    )
    return success_response({"items": items})


@require_GET
@require_auth()
def notificaciones_por_usuario_leida(request, user_id: int):
    if request.usuario_actual.rol != "admin" and user_id != request.usuario_actual.id:
        return error_response("No tienes permisos.", status=403)
    raw = request.GET.get("leida")
    if raw is None:
        return error_response("Parametro leida requerido.", status=400)
    leida = str(raw).lower() in ("1", "true", "yes")
    items = get_mensajeria_query_service().listar_notificaciones_filtradas(
        user_id, leida=leida
    )
    return success_response({"items": items})


@require_GET
@require_auth()
def notificaciones_por_usuario_rango(request, user_id: int):
    if request.usuario_actual.rol != "admin" and user_id != request.usuario_actual.id:
        return error_response("No tienes permisos.", status=403)
    desde_s = request.GET.get("desde")
    hasta_s = request.GET.get("hasta")
    if not desde_s or not hasta_s:
        return error_response("Parametros desde y hasta requeridos (ISO 8601).", status=400)
    desde = parse_datetime(desde_s)
    hasta = parse_datetime(hasta_s)
    if desde is None or hasta is None:
        return error_response("Fechas invalidas.", status=400)
    items = get_mensajeria_query_service().listar_notificaciones_filtradas(
        user_id, desde=desde, hasta=hasta
    )
    return success_response({"items": items})


