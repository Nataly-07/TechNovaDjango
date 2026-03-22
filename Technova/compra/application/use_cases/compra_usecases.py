from decimal import Decimal

from compra.domain.entities import CompraEntidad, ItemCompraEntidad
from compra.domain.repositories import CompraRepositoryPort
from compra.models import Compra
from producto.application.use_cases.producto_usecases import ProductoService


class CompraService:
    def __init__(self, compra_repository: CompraRepositoryPort, producto_service: ProductoService) -> None:
        self.compra_repository = compra_repository
        self.producto_service = producto_service

    def registrar_compra(self, compra: CompraEntidad) -> CompraEntidad:
        total_calculado = Decimal("0")
        for item in compra.items:
            self._validar_item(item)
            total_calculado += item.precio_unitario * item.cantidad

        compra_confirmada = CompraEntidad(
            id=compra.id,
            usuario_id=compra.usuario_id,
            proveedor_id=compra.proveedor_id,
            fecha_compra=compra.fecha_compra,
            total=total_calculado,
            estado=compra.estado,
            items=compra.items,
        )
        return self.compra_repository.guardar(compra_confirmada)

    def _validar_item(self, item: ItemCompraEntidad) -> None:
        if item.cantidad <= 0:
            raise ValueError("Cada item debe tener una cantidad mayor que cero.")
        if item.precio_unitario < 0:
            raise ValueError("El precio unitario no puede ser negativo.")

    def obtener_por_id(self, compra_id: int) -> CompraEntidad | None:
        return self.compra_repository.obtener_por_id(compra_id)

    def listar_todas(self) -> list[CompraEntidad]:
        return self.compra_repository.listar_todas()

    def listar_por_usuario(self, usuario_id: int) -> list[CompraEntidad]:
        return self.compra_repository.listar_por_usuario(usuario_id)

    def cambiar_estado(self, compra_id: int, estado: str) -> bool:
        validos = {c[0] for c in Compra.Estado.choices}
        if estado not in validos:
            raise ValueError(f"Estado invalido. Valores: {', '.join(sorted(validos))}")
        return self.compra_repository.actualizar_estado(compra_id, estado)
