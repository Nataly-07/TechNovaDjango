from django.db import transaction

from carrito.domain.entities import CarritoEntidad
from carrito.domain.repositories import CarritoRepositoryPort
from carrito.models import Carrito, DetalleCarrito


class CarritoOrmRepository(CarritoRepositoryPort):
    @transaction.atomic
    def guardar(self, carrito: CarritoEntidad) -> CarritoEntidad:
        carrito_model = Carrito.objects.create(
            usuario_id=carrito.usuario_id,
            estado=carrito.estado,
        )
        detalles = [
            DetalleCarrito(
                carrito=carrito_model,
                producto_id=item.producto_id,
                cantidad=item.cantidad,
            )
            for item in carrito.items
        ]
        DetalleCarrito.objects.bulk_create(detalles)
        return CarritoEntidad(
            id=carrito_model.id,
            usuario_id=carrito_model.usuario_id,
            fecha_creacion=carrito_model.fecha_creacion,
            estado=carrito_model.estado,
            items=carrito.items,
        )
