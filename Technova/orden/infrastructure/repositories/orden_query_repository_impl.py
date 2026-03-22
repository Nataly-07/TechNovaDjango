from orden.domain.repositories import OrdenQueryPort
from orden.models import OrdenCompra


def _orden_a_dict(orden: OrdenCompra) -> dict:
    return {
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


class OrdenQueryRepository(OrdenQueryPort):
    def listar_ordenes(self) -> list[dict]:
        queryset = OrdenCompra.objects.prefetch_related("detalles").order_by("-id")
        return [_orden_a_dict(orden) for orden in queryset]

    def obtener_orden(self, orden_id: int) -> dict | None:
        orden = OrdenCompra.objects.prefetch_related("detalles").filter(id=orden_id).first()
        return _orden_a_dict(orden) if orden else None
