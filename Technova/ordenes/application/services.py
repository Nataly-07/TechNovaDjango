from decimal import Decimal

from ordenes.domain.entities import OrdenCompraEntidad
from ordenes.domain.repositories import OrdenCompraRepositoryPort


class OrdenCompraService:
    def __init__(self, repository: OrdenCompraRepositoryPort) -> None:
        self.repository = repository

    def registrar_orden(self, orden: OrdenCompraEntidad) -> OrdenCompraEntidad:
        total = Decimal("0")
        for item in orden.items:
            if item.cantidad <= 0:
                raise ValueError("Cada item debe tener cantidad mayor a cero.")
            total += item.subtotal
        orden_calculada = OrdenCompraEntidad(
            id=orden.id,
            proveedor_id=orden.proveedor_id,
            fecha=orden.fecha,
            total=total,
            estado=orden.estado,
            items=orden.items,
        )
        return self.repository.guardar(orden_calculada)
