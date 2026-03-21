from django.db import transaction

from ordenes.domain.entities import OrdenCompraEntidad
from ordenes.domain.repositories import OrdenCompraRepositoryPort
from ordenes.models import DetalleOrden, OrdenCompra


class OrdenCompraOrmRepository(OrdenCompraRepositoryPort):
    @transaction.atomic
    def guardar(self, orden: OrdenCompraEntidad) -> OrdenCompraEntidad:
        orden_model = OrdenCompra.objects.create(
            proveedor_id=orden.proveedor_id,
            fecha=orden.fecha,
            total=orden.total,
            estado=orden.estado,
        )
        detalles = [
            DetalleOrden(
                orden_compra=orden_model,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                subtotal=item.subtotal,
            )
            for item in orden.items
        ]
        DetalleOrden.objects.bulk_create(detalles)
        return OrdenCompraEntidad(
            id=orden_model.id,
            proveedor_id=orden_model.proveedor_id,
            fecha=orden_model.fecha,
            total=orden_model.total,
            estado=orden_model.estado,
            items=orden.items,
        )
