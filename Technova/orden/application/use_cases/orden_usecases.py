from decimal import Decimal

from orden.domain.entities import OrdenCompraEntidad
from orden.domain.repositories import OrdenCompraRepositoryPort, OrdenQueryPort
from orden.domain.value_objects import Dinero
from orden.models import OrdenCompra


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

    def cambiar_estado(self, orden_id: int, estado: str) -> bool:
        validos = {c[0] for c in OrdenCompra.Estado.choices}
        if estado not in validos:
            raise ValueError(f"Estado invalido. Valores: {', '.join(sorted(validos))}")
        return self.repository.actualizar_estado(orden_id, estado)


class OrdenQueryService:
    def __init__(self, repository: OrdenQueryPort) -> None:
        self.repository = repository

    def listar_ordenes(self) -> list[dict]:
        return self.repository.listar_ordenes()

    def obtener_orden(self, orden_id: int) -> dict | None:
        return self.repository.obtener_orden(orden_id)
