from carrito.models import Carrito, Favorito
from carrito.domain.query_ports import CarritoQueryPort


class CarritoQueryRepository(CarritoQueryPort):
    def listar_carritos(self, usuario_id: int | None) -> list[dict]:
        queryset = Carrito.objects.prefetch_related("detalles").order_by("-id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        return [
            {
                "id": carrito.id,
                "usuario_id": carrito.usuario_id,
                "fecha_creacion": carrito.fecha_creacion.isoformat(),
                "estado": carrito.estado,
                "detalles": [
                    {"producto_id": detalle.producto_id, "cantidad": detalle.cantidad}
                    for detalle in carrito.detalles.all()
                ],
            }
            for carrito in queryset
        ]

    def listar_favoritos(self, usuario_id: int | None) -> list[dict]:
        queryset = Favorito.objects.select_related("producto").order_by("-id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [
            {
                "id": favorito.id,
                "usuario_id": favorito.usuario_id,
                "producto_id": favorito.producto_id,
                "producto_nombre": favorito.producto.nombre,
            }
            for favorito in queryset
        ]

    def crear_favorito(self, usuario_id: int, producto_id: int) -> int:
        favorito, _ = Favorito.objects.get_or_create(
            usuario_id=usuario_id,
            producto_id=producto_id,
        )
        return favorito.id
