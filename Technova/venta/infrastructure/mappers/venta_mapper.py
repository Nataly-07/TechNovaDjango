from venta.domain.entities import DetalleVentaEntidad, VentaEntidad
from venta.models import Venta


class VentaMapper:
    @staticmethod
    def to_domain(venta_model: Venta) -> VentaEntidad:
        return VentaEntidad(
            id=venta_model.id,
            usuario_id=venta_model.usuario_id,
            tipo_venta=getattr(venta_model, "tipo_venta", "online"),
            empleado_id=getattr(venta_model, "empleado_id", None),
            administrador_id=getattr(venta_model, "administrador_id", None),
            fecha_venta=venta_model.fecha_venta,
            estado=venta_model.estado,
            total=venta_model.total,
            detalles=[
                DetalleVentaEntidad(
                    producto_id=detalle.producto_id,
                    cantidad=detalle.cantidad,
                    precio_unitario=detalle.precio_unitario,
                )
                for detalle in venta_model.detalles.all()
            ],
        )
