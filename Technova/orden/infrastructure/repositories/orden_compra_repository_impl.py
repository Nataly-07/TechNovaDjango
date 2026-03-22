from django.db import transaction

from orden.domain.entities import OrdenCompraEntidad
from orden.domain.repositories import OrdenCompraRepositoryPort
from orden.infrastructure.mappers import OrdenMapper
from orden.models import DetalleOrden, OrdenCompra


class OrdenPersistenceAdapter(OrdenCompraRepositoryPort):
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
        orden_model = OrdenCompra.objects.prefetch_related("detalles").get(id=orden_model.id)
        return OrdenMapper.to_domain(orden_model)

    def actualizar_estado(self, orden_id: int, estado: str) -> bool:
        return OrdenCompra.objects.filter(id=orden_id).update(estado=estado) > 0
