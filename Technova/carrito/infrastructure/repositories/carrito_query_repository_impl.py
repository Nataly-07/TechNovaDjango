from carrito.domain.repositories import CarritoQueryPort
from carrito.models import Carrito, Favorito


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

    def eliminar_favorito(self, usuario_id: int, producto_id: int) -> bool:
        deleted, _ = Favorito.objects.filter(usuario_id=usuario_id, producto_id=producto_id).delete()
        return deleted > 0

    def _fav_a_dto(self, favorito: Favorito) -> dict:
        return {
            "id": favorito.id,
            "usuarioId": favorito.usuario_id,
            "productoId": favorito.producto_id,
        }

    def listar_favoritos_todos_dto(self) -> list[dict]:
        return [
            self._fav_a_dto(f)
            for f in Favorito.objects.order_by("-id")
        ]

    def listar_favoritos_usuario_dto(self, usuario_id: int) -> list[dict]:
        return [
            self._fav_a_dto(f)
            for f in Favorito.objects.filter(usuario_id=usuario_id).order_by("-id")
        ]

    def agregar_favorito_dto(self, usuario_id: int, producto_id: int) -> dict:
        favorito, _ = Favorito.objects.get_or_create(
            usuario_id=usuario_id,
            producto_id=producto_id,
        )
        return self._fav_a_dto(favorito)

    def toggle_favorito(self, usuario_id: int, producto_id: int) -> bool:
        deleted, _ = Favorito.objects.filter(usuario_id=usuario_id, producto_id=producto_id).delete()
        if deleted:
            return False
        Favorito.objects.create(usuario_id=usuario_id, producto_id=producto_id)
        return True

    def quitar_favorito_dto(self, usuario_id: int, producto_id: int) -> dict | None:
        try:
            favorito = Favorito.objects.get(usuario_id=usuario_id, producto_id=producto_id)
        except Favorito.DoesNotExist:
            return None
        data = self._fav_a_dto(favorito)
        favorito.delete()
        return data
