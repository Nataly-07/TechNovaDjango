from datetime import datetime
from decimal import Decimal

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from common.container import get_compra_service
from compras.domain.entities import CompraEntidad, ItemCompraEntidad


@csrf_exempt
@require_POST
@require_auth(roles=["admin", "empleado"])
def registrar_compra(request):
    try:
        payload = parse_json_body(request)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    usuario_objetivo_id = payload.get("usuario_id", request.usuario_actual.id)
    if request.usuario_actual.rol != "admin" and usuario_objetivo_id != request.usuario_actual.id:
        return error_response("No puedes registrar compras para otro usuario.", status=403)

    items = [
        ItemCompraEntidad(
            producto_id=item["producto_id"],
            cantidad=item["cantidad"],
            precio_unitario=Decimal(str(item["precio_unitario"])),
        )
        for item in payload.get("items", [])
    ]
    compra = CompraEntidad(
        id=None,
        usuario_id=usuario_objetivo_id,
        proveedor_id=payload["proveedor_id"],
        fecha_compra=datetime.fromisoformat(payload["fecha_compra"]),
        total=Decimal("0"),
        estado=payload.get("estado", "registrada"),
        items=items,
    )
    service = get_compra_service()
    try:
        compra_guardada = service.registrar_compra(compra)
    except (KeyError, ValueError) as exc:
        return error_response(str(exc), status=400)
    return success_response(
        {
            "id": compra_guardada.id,
            "total": str(compra_guardada.total),
            "estado": compra_guardada.estado,
        },
        status=201,
        message="Compra registrada",
    )
