from datetime import datetime
from decimal import Decimal

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_envio_query_service, get_envio_service
from envio.domain.entities import EnvioEntidad
from envio.models import Envio


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
        estado_raw = payload.get("estado", Envio.Estado.PREPARANDO)
        estados_ok = {c[0] for c in Envio.Estado.choices}
        if estado_raw not in estados_ok:
            return error_response(
                f"Estado invalido. Use uno de: {', '.join(sorted(estados_ok))}", status=400
            )
        envio = EnvioEntidad(
            id=None,
            venta_id=payload["venta_id"],
            transportadora_id=payload["transportadora_id"],
            fecha_envio=fecha_envio,
            numero_guia=payload["numero_guia"],
            costo_envio=Decimal(str(payload.get("costo_envio", "0"))),
            estado=estado_raw,
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


@require_GET
@require_auth(roles=["admin", "empleado"])
def envio_por_id_get(request, envio_id: int):
    data = get_envio_query_service().obtener_envio(envio_id)
    if data is None:
        return error_response("Envio no encontrado.", status=404)
    return success_response(data)


@csrf_exempt
@require_http_methods(["PUT"])
@require_auth(roles=["admin", "empleado"])
def envio_por_id_put(request, envio_id: int):
    try:
        payload = parse_json_body(request)
        fecha_envio = datetime.fromisoformat(payload["fecha_envio"])
        if timezone.is_naive(fecha_envio):
            fecha_envio = timezone.make_aware(fecha_envio, timezone.get_current_timezone())
        estado = payload.get("estado", Envio.Estado.PREPARANDO)
        estados_ok = {c[0] for c in Envio.Estado.choices}
        if estado not in estados_ok:
            return error_response(
                f"Estado invalido. Use uno de: {', '.join(sorted(estados_ok))}", status=400
            )
        envio = EnvioEntidad(
            id=envio_id,
            venta_id=int(payload["venta_id"]),
            transportadora_id=int(payload["transportadora_id"]),
            fecha_envio=fecha_envio,
            numero_guia=str(payload["numero_guia"]).strip(),
            costo_envio=Decimal(str(payload.get("costo_envio", "0"))),
            estado=estado,
        )
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    try:
        actualizado = get_envio_service().actualizar_envio(envio)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    return success_response(
        {"id": actualizado.id, "numero_guia": actualizado.numero_guia, "estado": actualizado.estado}
    )


@csrf_exempt
@require_http_methods(["DELETE"])
@require_auth(roles=["admin", "empleado"])
def envio_por_id_delete(request, envio_id: int):
    if not get_envio_service().eliminar_envio(envio_id):
        return error_response("Envio no encontrado.", status=404)
    return success_response({}, message="Envio desactivado")


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
@require_auth(roles=["admin", "empleado"])
def envio_por_id(request, envio_id: int):
    if request.method == "GET":
        return envio_por_id_get(request, envio_id)
    if request.method == "PUT":
        return envio_por_id_put(request, envio_id)
    return envio_por_id_delete(request, envio_id)
