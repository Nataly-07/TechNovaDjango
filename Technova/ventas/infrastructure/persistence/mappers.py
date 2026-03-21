from ventas.domain.entities import DetalleVentaEntidad, VentaEntidad
from ventas.models import Venta


class VentaMapper:
    @staticmethod
    def to_domain(venta_model: Venta) -> VentaEntidad:
        return VentaEntidad(
            id=venta_model.id,
            usuario_id=venta_model.usuario_id,
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
