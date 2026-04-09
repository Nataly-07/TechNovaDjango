from venta.domain.repositories import VentaQueryPort
from venta.infrastructure.mappers import VentaMapper
from venta.models import Venta


def _venta_a_dict(venta) -> dict:
    return {
        "id": venta.id,
        "usuario_id": venta.usuario_id,
        "tipo_venta": getattr(venta, "tipo_venta", "online"),
        "empleado_id": getattr(venta, "empleado_id", None),
        "administrador_id": getattr(venta, "administrador_id", None),
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


class VentaQueryRepository(VentaQueryPort):
    def listar_ventas(self) -> list[dict]:
        queryset = Venta.objects.prefetch_related("detalles").order_by("-id")
        ventas = [VentaMapper.to_domain(venta) for venta in queryset]
        return [_venta_a_dict(v) for v in ventas]

    def obtener_venta(self, venta_id: int) -> dict | None:
        model = Venta.objects.prefetch_related("detalles").filter(id=venta_id).first()
        if model is None:
            return None
        venta = VentaMapper.to_domain(model)
        return _venta_a_dict(venta)

    def listar_ventas_por_usuario(self, usuario_id: int) -> list[dict]:
        queryset = (
            Venta.objects.prefetch_related("detalles").filter(usuario_id=usuario_id).order_by("-id")
        )
        ventas = [VentaMapper.to_domain(venta) for venta in queryset]
        return [_venta_a_dict(v) for v in ventas]
