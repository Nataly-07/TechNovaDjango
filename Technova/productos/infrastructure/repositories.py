from decimal import Decimal

from productos.domain.entities import ProductoEntidad
from productos.domain.repositories import ProductoRepositoryPort
from productos.models import Producto


class ProductoOrmRepository(ProductoRepositoryPort):
    def _to_entity(self, model: Producto) -> ProductoEntidad:
        return ProductoEntidad(
            id=model.id,
            codigo=model.codigo,
            nombre=model.nombre,
            proveedor_id=model.proveedor_id,
            stock=model.stock,
            costo_unitario=Decimal(model.costo_unitario),
            activo=model.activo,
        )

    def obtener_por_id(self, producto_id: int) -> ProductoEntidad | None:
        try:
            model = Producto.objects.get(id=producto_id)
        except Producto.DoesNotExist:
            return None
        return self._to_entity(model)

    def listar_activos(self) -> list[ProductoEntidad]:
        queryset = Producto.objects.filter(activo=True).order_by("id")
        return [self._to_entity(model) for model in queryset]

    def guardar(self, producto: ProductoEntidad) -> ProductoEntidad:
        model = Producto.objects.get(id=producto.id)
        model.stock = producto.stock
        model.costo_unitario = producto.costo_unitario
        model.activo = producto.activo
        model.save(update_fields=["stock", "costo_unitario", "activo", "actualizado_en"])
        return self._to_entity(model)
