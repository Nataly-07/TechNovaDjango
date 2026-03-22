from datetime import datetime

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_atencion_query_service, get_atencion_service
from atencion_cliente.domain.entities import AtencionClienteEntidad


@require_GET
@require_auth()
def listar_solicitudes(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    query_service = get_atencion_query_service()
    return success_response({"items": query_service.listar_solicitudes(usuario_id)})


@csrf_exempt
@require_POST
@require_auth()
def crear_solicitud(request):
    try:
        payload = parse_json_body(request)
        usuario_objetivo_id = payload.get("usuario_id", request.usuario_actual.id)
        if request.usuario_actual.rol != "admin" and usuario_objetivo_id != request.usuario_actual.id:
            return error_response("No puedes crear solicitudes para otro usuario.", status=403)
        fecha_consulta = datetime.fromisoformat(payload["fecha_consulta"])
        if timezone.is_naive(fecha_consulta):
            fecha_consulta = timezone.make_aware(fecha_consulta, timezone.get_current_timezone())
        solicitud = AtencionClienteEntidad(
            id=None,
            usuario_id=usuario_objetivo_id,
            fecha_consulta=fecha_consulta,
            tema=payload["tema"],
            descripcion=payload["descripcion"],
            estado=payload.get("estado", "abierta"),
            respuesta=payload.get("respuesta", ""),
        )
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    service = get_atencion_service()
    try:
        guardada = service.crear_solicitud(solicitud)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    return success_response({"id": guardada.id, "estado": guardada.estado}, status=201)


@require_GET
@require_auth()
def listar_reclamos(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    query_service = get_atencion_query_service()
    return success_response({"items": query_service.listar_reclamos(usuario_id)})


@csrf_exempt
@require_POST
@require_auth()
def crear_reclamo(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    usuario_objetivo_id = payload.get("usuario_id", request.usuario_actual.id)
    if request.usuario_actual.rol != "admin" and usuario_objetivo_id != request.usuario_actual.id:
        return error_response("No puedes crear reclamos para otro usuario.", status=403)

    try:
        fecha_reclamo = datetime.fromisoformat(payload["fecha_reclamo"])
        if timezone.is_naive(fecha_reclamo):
            fecha_reclamo = timezone.make_aware(fecha_reclamo, timezone.get_current_timezone())
        resultado = get_atencion_query_service().crear_reclamo(
            {
                "usuario_id": usuario_objetivo_id,
                "fecha_reclamo": fecha_reclamo,
                "titulo": payload["titulo"],
                "descripcion": payload["descripcion"],
                "estado": payload.get("estado", "pendiente"),
                "respuesta": payload.get("respuesta", ""),
                "prioridad": payload.get("prioridad", "normal"),
                "enviado_al_admin": payload.get("enviado_al_admin", False),
                "evaluacion_cliente": payload.get("evaluacion_cliente", ""),
            }
        )
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    return success_response(resultado, status=201)
