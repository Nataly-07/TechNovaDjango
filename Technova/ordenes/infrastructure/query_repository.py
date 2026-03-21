from ordenes.models import OrdenCompra
from ordenes.domain.query_ports import OrdenesQueryPort


class OrdenesQueryRepository(OrdenesQueryPort):
    def listar_ordenes(self) -> list[dict]:
        queryset = OrdenCompra.objects.prefetch_related("detalles").order_by("-id")
        return [
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
