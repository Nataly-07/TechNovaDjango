from productos.domain.entities import ProductoEntidad
from productos.domain.repositories import ProductoRepositoryPort


class ProductoService:
    def __init__(self, repository: ProductoRepositoryPort) -> None:
        self.repository = repository

    def listar_productos_activos(self) -> list[ProductoEntidad]:
        return self.repository.listar_activos()

    def descontar_stock(self, producto_id: int, cantidad: int) -> ProductoEntidad:
        producto = self.repository.obtener_por_id(producto_id)
        if producto is None or not producto.activo:
            raise ValueError("El producto no existe o no esta activo.")

        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor que cero.")

        if producto.stock < cantidad:
            raise ValueError("Stock insuficiente para completar la operacion.")

        actualizado = ProductoEntidad(
            id=producto.id,
            codigo=producto.codigo,
            nombre=producto.nombre,
            proveedor_id=producto.proveedor_id,
            stock=producto.stock - cantidad,
            costo_unitario=producto.costo_unitario,
            activo=producto.activo,
        )
        return self.repository.guardar(actualizado)
