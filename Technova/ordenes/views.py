from datetime import date
from decimal import Decimal

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from common.api import error_response, parse_json_body, success_response
from common.auth import require_auth
from ordenes.application.services import OrdenCompraService
from ordenes.domain.entities import ItemOrdenEntidad, OrdenCompraEntidad
from ordenes.infrastructure.repositories import OrdenCompraOrmRepository
from ordenes.models import OrdenCompra


@require_GET
@require_auth(roles=["admin", "empleado"])
def listar_ordenes(request):
    queryset = OrdenCompra.objects.prefetch_related("detalles").order_by("-id")
    return success_response(
        {
            "items": [
                {
                    "id": orden.id,
                    "proveedor_id": orden.proveedor_id,
                    "fecha": orden.fecha.isoformat(),
                    "total": str(orden.total),
                    "estado": orden.estado,
                    "detalles": [
                        {
                            "producto_id": detalle.producto_id,
                            "cantidad": detalle.cantidad,
                            "precio_unitario": str(detalle.precio_unitario),
                            "subtotal": str(detalle.subtotal),
                        }
                        for detalle in orden.detalles.all()
                    ],
                }
                for orden in queryset
            ]
        }
    )


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
    service = OrdenCompraService(OrdenCompraOrmRepository())
    try:
        guardada = service.registrar_orden(orden)
    except ValueError as exc:
        return error_response(str(exc), status=400)
    return success_response({"id": guardada.id, "total": str(guardada.total)}, status=201)
