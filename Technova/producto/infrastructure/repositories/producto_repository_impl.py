from decimal import Decimal

from django.db.models import DecimalField, Q
from django.db.models.functions import Coalesce

from producto.domain.entities import ProductoEntidad
from producto.domain.repositories import ProductoRepositoryPort
from producto.models import Producto


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
            imagen_url=model.imagen_url or "",
            categoria=model.categoria or "",
            marca=model.marca or "",
            color=model.color or "",
            descripcion=model.descripcion or "",
            precio_venta=Decimal(model.precio_venta) if model.precio_venta is not None else None,
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

    def listar_todos(self) -> list[ProductoEntidad]:
        queryset = Producto.objects.order_by("id")
        return [self._to_entity(model) for model in queryset]

    def guardar(self, producto: ProductoEntidad) -> ProductoEntidad:
        model = Producto.objects.get(id=producto.id)
        model.stock = producto.stock
        model.costo_unitario = producto.costo_unitario
        model.activo = producto.activo
        model.save(update_fields=["stock", "costo_unitario", "activo", "actualizado_en"])
        return self._to_entity(model)

    def crear(self, producto: ProductoEntidad) -> ProductoEntidad:
        model = Producto.objects.create(
            codigo=producto.codigo,
            nombre=producto.nombre,
            proveedor_id=producto.proveedor_id,
            stock=producto.stock,
            costo_unitario=producto.costo_unitario,
            activo=producto.activo,
            imagen_url=producto.imagen_url or "",
            categoria=producto.categoria or "",
            marca=producto.marca or "",
            color=producto.color or "",
            descripcion=producto.descripcion or "",
            precio_venta=producto.precio_venta,
        )
        return self._to_entity(model)

    def actualizar_completo(self, producto: ProductoEntidad) -> ProductoEntidad | None:
        if producto.id is None:
            return None
        try:
            model = Producto.objects.get(id=producto.id)
        except Producto.DoesNotExist:
            return None
        model.codigo = producto.codigo
        model.nombre = producto.nombre
        model.proveedor_id = producto.proveedor_id
        model.stock = producto.stock
        model.costo_unitario = producto.costo_unitario
        model.activo = producto.activo
        model.imagen_url = producto.imagen_url or ""
        model.categoria = producto.categoria or ""
        model.marca = producto.marca or ""
        model.color = producto.color or ""
        model.descripcion = producto.descripcion or ""
        model.precio_venta = producto.precio_venta
        model.save()
        return self._to_entity(model)

    def marcar_inactivo(self, producto_id: int) -> bool:
        return Producto.objects.filter(id=producto_id).update(activo=False) > 0

    def establecer_activo(self, producto_id: int, activo: bool) -> ProductoEntidad | None:
        updated = Producto.objects.filter(id=producto_id).update(activo=activo)
        if not updated:
            return None
        return self.obtener_por_id(producto_id)

    def listar_por_categoria(self, categoria: str) -> list[ProductoEntidad]:
        queryset = Producto.objects.filter(activo=True, categoria__iexact=categoria.strip()).order_by(
            "id"
        )
        return [self._to_entity(m) for m in queryset]

    def listar_por_marca(self, marca: str) -> list[ProductoEntidad]:
        queryset = Producto.objects.filter(activo=True, marca__iexact=marca.strip()).order_by("id")
        return [self._to_entity(m) for m in queryset]

    def buscar_nombre_paginado(
        self, termino: str, page: int, size: int
    ) -> tuple[list[ProductoEntidad], int]:
        qs = Producto.objects.filter(activo=True, nombre__icontains=termino.strip()).order_by("id")
        total = qs.count()
        start = max(page, 0) * max(size, 1)
        slice_qs = qs[start : start + max(size, 1)]
        return [self._to_entity(m) for m in slice_qs], total

    def listar_rango_precio_paginado(
        self, min_p: Decimal, max_p: Decimal, page: int, size: int
    ) -> tuple[list[ProductoEntidad], int]:
        qs = (
            Producto.objects.filter(activo=True)
            .annotate(
                precio_pub=Coalesce("precio_venta", "costo_unitario", output_field=DecimalField())
            )
            .filter(precio_pub__gte=min_p, precio_pub__lte=max_p)
            .order_by("id")
        )
        total = qs.count()
        start = max(page, 0) * max(size, 1)
        slice_qs = qs[start : start + max(size, 1)]
        return [self._to_entity(m) for m in slice_qs], total

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
        qs = Producto.objects.filter(activo=True)
        if termino and termino.strip():
            qs = qs.filter(
                Q(nombre__icontains=termino.strip()) | Q(descripcion__icontains=termino.strip())
            )
        if marca and marca.strip():
            qs = qs.filter(marca__iexact=marca.strip())
        if categoria and categoria.strip():
            qs = qs.filter(categoria__iexact=categoria.strip())
        if disponibilidad and disponibilidad.strip().lower() == "disponible":
            qs = qs.filter(stock__gt=0)
        elif disponibilidad and disponibilidad.strip().lower() == "agotado":
            qs = qs.filter(stock=0)

        qs = qs.annotate(
            precio_pub=Coalesce("precio_venta", "costo_unitario", output_field=DecimalField())
        )
        if precio_min is not None:
            qs = qs.filter(precio_pub__gte=precio_min)
        if precio_max is not None:
            qs = qs.filter(precio_pub__lte=precio_max)

        return [self._to_entity(m) for m in qs.order_by("id")]
