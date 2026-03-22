from datetime import date
from decimal import Decimal

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_orden_query_service, get_orden_service
from orden.domain.entities import ItemOrdenEntidad, OrdenCompraEntidad
from orden.models import OrdenCompra


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_ordenes(request):
    query_service = get_orden_query_service()
    return success_response({"items": query_service.listar_ordenes()})


@require_GET
@require_auth(roles=["admin", "empleado"])
def detalle_orden(request, orden_id: int):
    data = get_orden_query_service().obtener_orden(orden_id)
    if data is None:
        return error_response("Orden no encontrada.", status=404)
    return success_response(data)


@csrf_exempt
@require_http_methods(["PATCH"])
@require_auth(roles=["admin", "empleado"])
def actualizar_estado_orden(request, orden_id: int):
    try:
        body = parse_json_body(request)
        estado = str(body.get("estado", "")).strip()
    except ValueError as exc:
        return error_response(str(exc), status=400)
    if not estado:
        return error_response("Campo estado requerido.", status=400)
    try:
        ok = get_orden_service().cambiar_estado(orden_id, estado)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    if not ok:
        return error_response("Orden no encontrada.", status=404)
    return success_response({}, message="Estado actualizado")


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def registrar_orden(request):
    try:
        payload = parse_json_body(request)
        items = [
            ItemOrdenEntidad(
                producto_id=item["producto_id"],
                cantidad=item["cantidad"],
                precio_unitario=Decimal(str(item["precio_unitario"])),
                subtotal=Decimal(str(item["subtotal"])),
            )
            for item in payload.get("items", [])
        ]
        estado_raw = payload.get("estado", OrdenCompra.Estado.PENDIENTE)
        estados_ok = {c[0] for c in OrdenCompra.Estado.choices}
        if estado_raw not in estados_ok:
            return error_response(
                f"Estado invalido. Use uno de: {', '.join(sorted(estados_ok))}", status=400
            )
        orden = OrdenCompraEntidad(
            id=None,
            proveedor_id=payload["proveedor_id"],
            fecha=date.fromisoformat(payload["fecha"]),
            total=Decimal("0"),
            estado=estado_raw,
            items=items,
        )
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    service = get_orden_service()
    try:
        guardada = service.registrar_orden(orden)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    return success_response({"id": guardada.id, "total": str(guardada.total)}, status=201)
