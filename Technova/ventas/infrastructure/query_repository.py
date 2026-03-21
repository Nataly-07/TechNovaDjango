from ventas.models import Venta
from ventas.domain.ports import VentaQueryPort
from ventas.infrastructure.persistence.mappers import VentaMapper


class VentasQueryRepository(VentaQueryPort):
    def listar_ventas(self) -> list[dict]:
        queryset = Venta.objects.prefetch_related("detalles").order_by("-id")
        ventas = [VentaMapper.to_domain(venta) for venta in queryset]
        return [
            {
                "id": venta.id,
                "usuario_id": venta.usuario_id,
                "fecha_venta": venta.fecha_venta.isoformat(),
                "estado": venta.estado,
                "total": str(venta.total),
                "detalles": [
                    {
                        "producto_id": detalle.producto_id,
                        "cantidad": detalle.cantidad,
                        "precio_unitario": str(detalle.precio_unitario),
                    }
                    for detalle in venta.detalles
                ],
            }
            for venta in ventas
        ]
