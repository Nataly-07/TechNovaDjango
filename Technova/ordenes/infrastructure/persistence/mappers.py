from ordenes.domain.entities import ItemOrdenEntidad, OrdenCompraEntidad
from ordenes.models import OrdenCompra


class OrdenMapper:
    @staticmethod
    def to_domain(orden_model: OrdenCompra) -> OrdenCompraEntidad:
        return OrdenCompraEntidad(
            id=orden_model.id,
            proveedor_id=orden_model.proveedor_id,
            fecha=orden_model.fecha,
            total=orden_model.total,
            estado=orden_model.estado,
            items=[
                ItemOrdenEntidad(
                    producto_id=detalle.producto_id,
                    cantidad=detalle.cantidad,
                    precio_unitario=detalle.precio_unitario,
                    subtotal=detalle.subtotal,
                )
                for detalle in orden_model.detalles.all()
            ],
        )
