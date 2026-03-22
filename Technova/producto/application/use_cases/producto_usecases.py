from decimal import Decimal

from producto.domain.entities import ProductoEntidad
from producto.domain.repositories import ProductoRepositoryPort


class ProductoService:
    def __init__(self, repository: ProductoRepositoryPort) -> None:
        self.repository = repository

    def listar_productos_activos(self) -> list[ProductoEntidad]:
        return self.repository.listar_activos()

    def listar_todos(self) -> list[ProductoEntidad]:
        return self.repository.listar_todos()

    def obtener_por_id(self, producto_id: int) -> ProductoEntidad | None:
        return self.repository.obtener_por_id(producto_id)

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
            imagen_url=producto.imagen_url,
            categoria=producto.categoria,
            marca=producto.marca,
            descripcion=producto.descripcion,
            precio_venta=producto.precio_venta,
        )
        return self.repository.guardar(actualizado)

    def crear(self, entidad: ProductoEntidad) -> ProductoEntidad:
        return self.repository.crear(entidad)

    def actualizar(self, entidad: ProductoEntidad) -> ProductoEntidad | None:
        return self.repository.actualizar_completo(entidad)

    def eliminar(self, producto_id: int) -> bool:
        return self.repository.marcar_inactivo(producto_id)

    def cambiar_estado(self, producto_id: int, activo: bool) -> ProductoEntidad | None:
        return self.repository.establecer_activo(producto_id, activo)

    def por_categoria(self, categoria: str) -> list[ProductoEntidad]:
        return self.repository.listar_por_categoria(categoria)

    def por_marca(self, marca: str) -> list[ProductoEntidad]:
        return self.repository.listar_por_marca(marca)

    def buscar_paginado(self, termino: str, page: int, size: int) -> tuple[list[ProductoEntidad], int]:
        return self.repository.buscar_nombre_paginado(termino, page, size)

    def por_rango_precio(
        self, min_p: Decimal, max_p: Decimal, page: int, size: int
    ) -> tuple[list[ProductoEntidad], int]:
        return self.repository.listar_rango_precio_paginado(min_p, max_p, page, size)

    def buscar_avanzado(
        self,
        *,
        termino: str | None,
        marca: str | None,
        categoria: str | None,
        precio_min: Decimal | None,
        precio_max: Decimal | None,
        disponibilidad: str | None,
    ) -> list[ProductoEntidad]:
        return self.repository.buscar_avanzado(
            termino=termino,
            marca=marca,
            categoria=categoria,
            precio_min=precio_min,
            precio_max=precio_max,
            disponibilidad=disponibilidad,
        )
