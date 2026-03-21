from decimal import Decimal

from ordenes.domain.entities import OrdenCompraEntidad
from ordenes.domain.repositories import OrdenCompraRepositoryPort
from ordenes.domain.value_objects import Dinero


class OrdenCompraService:
    def __init__(self, repository: OrdenCompraRepositoryPort) -> None:
        self.repository = repository

    def registrar_orden(self, orden: OrdenCompraEntidad) -> OrdenCompraEntidad:
        total = Decimal("0")
        for item in orden.items:
            if item.cantidad <= 0:
                raise ValueError("Cada item debe tener cantidad mayor a cero.")
            Dinero.crear(item.precio_unitario)
            Dinero.crear(item.subtotal)
            total += item.subtotal
        Dinero.crear(total)
        orden_calculada = OrdenCompraEntidad(
            id=orden.id,
            proveedor_id=orden.proveedor_id,
            fecha=orden.fecha,
            total=total,
            estado=orden.estado,
            items=orden.items,
        )
        return self.repository.guardar(orden_calculada)
