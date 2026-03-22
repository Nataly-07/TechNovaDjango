from django.db import transaction

from compra.domain.entities import CompraEntidad, ItemCompraEntidad
from compra.domain.repositories import CompraRepositoryPort
from compra.models import Compra, DetalleCompra


class CompraOrmRepository(CompraRepositoryPort):
    def _to_entity(self, model: Compra) -> CompraEntidad:
        detalles = list(model.detalles.all())
        items = [
            ItemCompraEntidad(
                producto_id=d.producto_id,
                cantidad=d.cantidad,
                precio_unitario=d.precio_unitario,
            )
            for d in detalles
        ]
        return CompraEntidad(
            id=model.id,
            usuario_id=model.usuario_id,
            proveedor_id=model.proveedor_id,
            fecha_compra=model.fecha_compra,
            total=model.total,
            estado=model.estado,
            items=items,
        )

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

        compra_model = Compra.objects.prefetch_related("detalles").get(id=compra_model.id)
        return self._to_entity(compra_model)

    def obtener_por_id(self, compra_id: int) -> CompraEntidad | None:
        model = Compra.objects.prefetch_related("detalles").filter(id=compra_id).first()
        return self._to_entity(model) if model else None

    def listar_todas(self) -> list[CompraEntidad]:
        qs = Compra.objects.prefetch_related("detalles").order_by("-fecha_compra", "-id")
        return [self._to_entity(m) for m in qs]

    def listar_por_usuario(self, usuario_id: int) -> list[CompraEntidad]:
        qs = (
            Compra.objects.prefetch_related("detalles")
            .filter(usuario_id=usuario_id)
            .order_by("-fecha_compra", "-id")
        )
        return [self._to_entity(m) for m in qs]

    def actualizar_estado(self, compra_id: int, estado: str) -> bool:
        return Compra.objects.filter(id=compra_id).update(estado=estado) > 0
