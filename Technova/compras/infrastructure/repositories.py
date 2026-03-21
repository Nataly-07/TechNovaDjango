from django.db import transaction

from compras.domain.entities import CompraEntidad
from compras.domain.repositories import CompraRepositoryPort
from compras.models import Compra, DetalleCompra


class CompraOrmRepository(CompraRepositoryPort):
    @transaction.atomic
    def guardar(self, compra: CompraEntidad) -> CompraEntidad:
        compra_model = Compra.objects.create(
            usuario_id=compra.usuario_id,
            proveedor_id=compra.proveedor_id,
            total=compra.total,
            estado=compra.estado,
            fecha_compra=compra.fecha_compra,
        )
        detalles = [
            DetalleCompra(
                compra=compra_model,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
            )
            for item in compra.items
        ]
        DetalleCompra.objects.bulk_create(detalles)

        return CompraEntidad(
            id=compra_model.id,
            usuario_id=compra_model.usuario_id,
            proveedor_id=compra_model.proveedor_id,
            fecha_compra=compra_model.fecha_compra,
            total=compra_model.total,
            estado=compra_model.estado,
            items=compra.items,
        )
