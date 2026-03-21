from datetime import date
from decimal import Decimal

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_orden_query_service, get_orden_service
from ordenes.domain.entities import ItemOrdenEntidad, OrdenCompraEntidad


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_ordenes(request):
    query_service = get_orden_query_service()
    return success_response({"items": query_service.listar_ordenes()})


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
        orden = OrdenCompraEntidad(
            id=None,
            proveedor_id=payload["proveedor_id"],
            fecha=date.fromisoformat(payload["fecha"]),
            total=Decimal("0"),
            estado=payload.get("estado", "pendiente"),
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
