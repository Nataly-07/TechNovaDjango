from datetime import datetime

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_atencion_query_service, get_atencion_service
from atencion_cliente.domain.entities import AtencionClienteEntidad
from atencion_cliente.models import AtencionCliente


def _solicitud_to_dict(s: AtencionCliente) -> dict:
    return {
        "id": s.id,
        "usuarioId": s.usuario_id,  # compat JS legacy
        "usuario_id": s.usuario_id,
        "fechaConsulta": s.fecha_consulta.isoformat(),
        "fecha_consulta": s.fecha_consulta.isoformat(),
        "tema": s.tema,
        "descripcion": s.descripcion,
        "estado": s.estado,
        "respuesta": s.respuesta or "",
    }


@require_GET
@require_auth()
def listar_solicitudes(request):
    usuario_id = request.GET.get("usuario_id")
    if request.usuario_actual.rol != "admin":
        usuario_id = request.usuario_actual.id
    query_service = get_atencion_query_service()
    return success_response({"items": query_service.listar_solicitudes(usuario_id)})


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_solicitudes_por_usuario(request, usuario_id: int):
    query_service = get_atencion_query_service()
    return success_response({"items": query_service.listar_solicitudes(usuario_id)})


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_solicitudes_por_estado(request, estado: str):
    """
    Java lista por estado; en Django usamos estados: abierta/en_proceso/cerrada.
    Se acepta 'pendientes' como alias a (abierta + en_proceso).
    """
    e = (estado or "").strip().lower()
    qs = AtencionCliente.objects.order_by("-id")
    if e == "pendientes":
        qs = qs.filter(estado__in=[AtencionCliente.Estado.ABIERTA, AtencionCliente.Estado.EN_PROCESO])
    else:
        qs = qs.filter(estado=e)
    return success_response({"items": [_solicitud_to_dict(s) for s in qs]})


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


@csrf_exempt
@require_POST
@require_auth()
def crear_ticket_java(request):
    """
    Endpoint estilo JavaSpringBoot:
      POST /api/atencion-cliente?usuarioId=...&tema=...&descripcion=...
    o body x-www-form-urlencoded.
    """
    try:
        usuario_id = request.GET.get("usuarioId") or request.POST.get("usuarioId")
        tema = request.GET.get("tema") or request.POST.get("tema")
        descripcion = request.GET.get("descripcion") or request.POST.get("descripcion")
        try:
            usuario_id_int = int(usuario_id)
        except (TypeError, ValueError):
            usuario_id_int = request.usuario_actual.id

        if request.usuario_actual.rol not in ("admin", "empleado") and usuario_id_int != request.usuario_actual.id:
            return error_response("No puedes crear tickets para otro usuario.", status=403)

        solicitud = AtencionClienteEntidad(
            id=None,
            usuario_id=usuario_id_int,
            fecha_consulta=timezone.now(),
            tema=(tema or "").strip(),
            descripcion=(descripcion or "").strip(),
            estado=AtencionCliente.Estado.ABIERTA,
            respuesta="",
        )
        guardada = get_atencion_service().crear_solicitud(solicitud)
        s = AtencionCliente.objects.get(id=guardada.id)
        return success_response(_solicitud_to_dict(s), status=200)
    except ValueError as exc:
        return error_response(f"Error: {exc}", status=400)
    except Exception as exc:  # noqa: BLE001
        return error_response(f"Error interno del servidor: {exc}", status=500)


@require_GET
@require_auth()
def detalle_solicitud(request, solicitud_id: int):
    """
    Detalle de una solicitud (ticket) por ID.
    - Staff puede ver cualquiera.
    - Cliente solo la suya.
    """
    s = AtencionCliente.objects.filter(id=solicitud_id).first()
    if s is None:
        return error_response("Solicitud no encontrada.", status=404)
    if request.usuario_actual.rol not in ("admin", "empleado") and s.usuario_id != request.usuario_actual.id:
        return error_response("No tienes permisos.", status=403)
    return success_response(_solicitud_to_dict(s))


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth(roles=["admin", "empleado"])
def responder_solicitud(request, solicitud_id: int):
    """
    Responder una solicitud (equivalente a /api/atencion-cliente/{id}/responder en Java).
    Espera JSON: { "respuesta": "..." } o form-data.
    """
    s = AtencionCliente.objects.filter(id=solicitud_id).first()
    if s is None:
        return error_response("Solicitud no encontrada.", status=404)
    respuesta = None
    try:
        payload = parse_json_body(request)
        respuesta = payload.get("respuesta")
    except ValueError:
        respuesta = request.POST.get("respuesta")
    respuesta = (respuesta or "").strip()
    if not respuesta:
        return error_response("La respuesta no puede estar vacía.", status=400)
    s.respuesta = respuesta
    if s.estado == AtencionCliente.Estado.ABIERTA:
        s.estado = AtencionCliente.Estado.EN_PROCESO
    s.save(update_fields=["respuesta", "estado", "actualizado_en"])
    return success_response(
        {
            "id": s.id,
            "usuarioId": s.usuario_id,
            "fechaConsulta": s.fecha_consulta.isoformat(),
            "tema": s.tema,
            "descripcion": s.descripcion,
            "estado": s.estado,
            "respuesta": s.respuesta,
        }
    )


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth(roles=["admin", "empleado"])
def cerrar_solicitud(request, solicitud_id: int):
    s = AtencionCliente.objects.filter(id=solicitud_id).first()
    if s is None:
        return error_response("Solicitud no encontrada.", status=404)
    s.estado = AtencionCliente.Estado.CERRADA
    s.save(update_fields=["estado", "actualizado_en"])
    return success_response({"id": s.id, "estado": s.estado})


@csrf_exempt
@require_http_methods(["DELETE"])
@require_auth(roles=["admin", "empleado"])
def eliminar_solicitud(request, solicitud_id: int):
    deleted, _ = AtencionCliente.objects.filter(id=solicitud_id).delete()
    if deleted <= 0:
        return error_response("Solicitud no encontrada.", status=404)
    return success_response({"ok": True})


@require_GET
@require_auth(roles=["admin", "empleado"])
def estadisticas_solicitudes(request):
    total = AtencionCliente.objects.count()
    pendientes = AtencionCliente.objects.filter(
        estado__in=[AtencionCliente.Estado.ABIERTA, AtencionCliente.Estado.EN_PROCESO]
    ).count()
    return success_response({"totalConsultas": total, "pendientes": pendientes})


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
