from datetime import datetime

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from atencion_cliente.application.services import AtencionClienteService
from atencion_cliente.domain.entities import AtencionClienteEntidad
from atencion_cliente.infrastructure.repositories import AtencionClienteOrmRepository
from atencion_cliente.models import AtencionCliente, Reclamo


@require_GET
@require_auth()
def listar_solicitudes(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    queryset = AtencionCliente.objects.order_by("-id")
    if usuario_id:
        queryset = queryset.filter(usuario_id=usuario_id)
    return success_response(
        {
            "items": [
                {
                    "id": solicitud.id,
                    "usuario_id": solicitud.usuario_id,
                    "fecha_consulta": solicitud.fecha_consulta.isoformat(),
                    "tema": solicitud.tema,
                    "descripcion": solicitud.descripcion,
                    "estado": solicitud.estado,
                    "respuesta": solicitud.respuesta,
                }
                for solicitud in queryset
            ]
        }
    )


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
    service = AtencionClienteService(AtencionClienteOrmRepository())
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
    queryset = Reclamo.objects.order_by("-id")
    if usuario_id:
        queryset = queryset.filter(usuario_id=usuario_id)
    return success_response(
        {
            "items": [
                {
                    "id": reclamo.id,
                    "usuario_id": reclamo.usuario_id,
                    "fecha_reclamo": reclamo.fecha_reclamo.isoformat(),
                    "titulo": reclamo.titulo,
                    "descripcion": reclamo.descripcion,
                    "estado": reclamo.estado,
                    "prioridad": reclamo.prioridad,
                }
                for reclamo in queryset
            ]
        }
    )


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
        reclamo = Reclamo.objects.create(
            usuario_id=usuario_objetivo_id,
            fecha_reclamo=fecha_reclamo,
            titulo=payload["titulo"],
            descripcion=payload["descripcion"],
            estado=payload.get("estado", "pendiente"),
            respuesta=payload.get("respuesta", ""),
            prioridad=payload.get("prioridad", "normal"),
            enviado_al_admin=payload.get("enviado_al_admin", False),
            evaluacion_cliente=payload.get("evaluacion_cliente", ""),
        )
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    return success_response({"id": reclamo.id, "estado": reclamo.estado}, status=201)
