from datetime import datetime
from decimal import Decimal

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_envio_query_service, get_envio_service
from envios.domain.entities import EnvioEntidad


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_envios(request):
    query_service = get_envio_query_service()
    return success_response({"items": query_service.listar_envios()})


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def registrar_envio(request):
    try:
        payload = parse_json_body(request)
        fecha_envio = datetime.fromisoformat(payload["fecha_envio"])
        if timezone.is_naive(fecha_envio):
            fecha_envio = timezone.make_aware(fecha_envio, timezone.get_current_timezone())
        envio = EnvioEntidad(
            id=None,
            venta_id=payload["venta_id"],
            transportadora_id=payload["transportadora_id"],
            fecha_envio=fecha_envio,
            numero_guia=payload["numero_guia"],
            costo_envio=Decimal(str(payload.get("costo_envio", "0"))),
            estado=payload.get("estado", "preparando"),
        )
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    service = get_envio_service()
    try:
        guardado = service.registrar_envio(envio)
    except ValueError as exc:
        return error_response(str(exc), status=400)

    return success_response({"id": guardado.id, "numero_guia": guardado.numero_guia}, status=201)


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_transportadoras(request):
    query_service = get_envio_query_service()
    return success_response({"items": query_service.listar_transportadoras()})


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def crear_transportadora(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    try:
        transportadora_id = get_envio_query_service().crear_transportadora(
            {
                "nombre": payload["nombre"],
                "telefono": payload["telefono"],
                "correo_electronico": payload["correo_electronico"],
                "activo": payload.get("activo", True),
            }
        )
    except (KeyError, ValueError) as exc:
        return error_response(f"Campo requerido faltante: {exc}", status=400)
    return success_response({"id": transportadora_id, "nombre": payload["nombre"]}, status=201)
