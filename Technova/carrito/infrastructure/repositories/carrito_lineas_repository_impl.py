from django.db import transaction

from carrito.domain.repositories import CarritoLineasPort
from carrito.models import Carrito, DetalleCarrito
from producto.models import Producto


class CarritoLineasRepository(CarritoLineasPort):
    def _carrito_activo(self, usuario_id: int) -> Carrito | None:
        return (
            Carrito.objects.filter(usuario_id=usuario_id, estado=Carrito.Estado.ACTIVO)
            .order_by("-fecha_creacion", "-id")
            .first()
        )

    def _obtener_o_crear_carrito_activo(self, usuario_id: int) -> Carrito:
        existente = self._carrito_activo(usuario_id)
        if existente:
            return existente
        return Carrito.objects.create(usuario_id=usuario_id, estado=Carrito.Estado.ACTIVO)

    def _lineas_a_dto(self, carrito: Carrito) -> list[dict]:
        detalles = (
            DetalleCarrito.objects.filter(carrito=carrito)
            .select_related("producto")
            .order_by("-id")
        )
        return [
            {
                "detalle_id": d.id,
                "producto_id": d.producto_id,
                "nombre_producto": d.producto.nombre,
                "imagen": d.producto.imagen_url or "",
                "cantidad": d.cantidad,
                "stock": d.producto.stock,
            }
            for d in detalles
        ]

    def listar_items(self, usuario_id: int) -> list[dict]:
        carrito = self._carrito_activo(usuario_id)
        if carrito is None:
            return []
        return self._lineas_a_dto(carrito)

    @transaction.atomic
    def agregar_producto(self, usuario_id: int, producto_id: int, cantidad: int) -> list[dict]:
        if cantidad < 1:
            cantidad = 1
        producto = Producto.objects.select_for_update().filter(id=producto_id).first()
        if producto is None:
            raise ValueError(f"Producto no encontrado: {producto_id}")
        if not producto.activo:
            raise ValueError("El producto no esta disponible.")
        if producto.stock is None or producto.stock <= 0:
            raise ValueError("El producto esta agotado y no se puede agregar al carrito")

        carrito = self._obtener_o_crear_carrito_activo(usuario_id)

        existente = (
            DetalleCarrito.objects.select_for_update()
            .filter(carrito=carrito, producto_id=producto_id)
            .first()
        )
        if existente:
            nueva_cantidad = existente.cantidad + cantidad
            if producto.stock < nueva_cantidad:
                raise ValueError("No hay suficiente stock disponible")
            existente.cantidad = nueva_cantidad
            existente.save(update_fields=["cantidad", "actualizado_en"])
            return self._lineas_a_dto(carrito)

        if producto.stock < cantidad:
            raise ValueError("No hay suficiente stock disponible")
        DetalleCarrito.objects.create(carrito=carrito, producto_id=producto_id, cantidad=cantidad)
        return self._lineas_a_dto(carrito)

    @transaction.atomic
    def actualizar_cantidad(self, usuario_id: int, detalle_id: int, cantidad: int) -> list[dict]:
        if cantidad < 1:
            cantidad = 1
        detalle = (
            DetalleCarrito.objects.select_for_update()
            .select_related("carrito", "producto")
            .filter(id=detalle_id)
            .first()
        )
        if detalle is None:
            raise ValueError(f"Detalle no encontrado: {detalle_id}")
        if detalle.carrito.usuario_id != usuario_id:
            raise ValueError("El detalle no pertenece al usuario.")
        if detalle.carrito.estado != Carrito.Estado.ACTIVO:
            raise ValueError("El carrito no esta activo.")
        producto = Producto.objects.select_for_update().filter(id=detalle.producto_id).first()
        if producto is None or not producto.activo:
            raise ValueError("El producto no esta disponible.")
        if producto.stock < cantidad:
            raise ValueError("No hay suficiente stock disponible")
        detalle.cantidad = cantidad
        detalle.save(update_fields=["cantidad", "actualizado_en"])
        return self._lineas_a_dto(detalle.carrito)

    @transaction.atomic
    def eliminar_detalle(self, usuario_id: int, detalle_id: int) -> list[dict]:
        detalle = (
            DetalleCarrito.objects.select_related("carrito")
            .filter(id=detalle_id)
            .first()
        )
        if detalle is None:
            raise ValueError(f"Detalle no encontrado: {detalle_id}")
        if detalle.carrito.usuario_id != usuario_id:
            raise ValueError("El detalle no pertenece al usuario.")
        if detalle.carrito.estado != Carrito.Estado.ACTIVO:
            raise ValueError("El carrito no esta activo.")
        carrito = detalle.carrito
        detalle.delete()
        return self._lineas_a_dto(carrito)

    @transaction.atomic
    def vaciar(self, usuario_id: int) -> None:
        carrito = self._obtener_o_crear_carrito_activo(usuario_id)
        DetalleCarrito.objects.filter(carrito=carrito).delete()
