from carrito.domain.entities import CarritoEntidad
from carrito.domain.repositories import CarritoLineasPort, CarritoQueryPort, CarritoRepositoryPort


class CarritoService:
    def __init__(self, repository: CarritoRepositoryPort) -> None:
        self.repository = repository

    def crear_carrito(self, carrito: CarritoEntidad) -> CarritoEntidad:
        if not carrito.items:
            raise ValueError("El carrito debe tener al menos un item.")
        for item in carrito.items:
            if item.cantidad <= 0:
                raise ValueError("La cantidad de cada item debe ser mayor a cero.")
        return self.repository.guardar(carrito)


class CarritoQueryService:
    def __init__(self, repository: CarritoQueryPort) -> None:
        self.repository = repository

    def listar_carritos(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_carritos(usuario_id)

    def listar_favoritos(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_favoritos(usuario_id)

    def crear_favorito(self, usuario_id: int, producto_id: int) -> int:
        return self.repository.crear_favorito(usuario_id, producto_id)

    def eliminar_favorito(self, usuario_id: int, producto_id: int) -> bool:
        return self.repository.eliminar_favorito(usuario_id, producto_id)

    def listar_favoritos_todos_dto(self) -> list[dict]:
        return self.repository.listar_favoritos_todos_dto()

    def listar_favoritos_usuario_dto(self, usuario_id: int) -> list[dict]:
        return self.repository.listar_favoritos_usuario_dto(usuario_id)

    def agregar_favorito_dto(self, usuario_id: int, producto_id: int) -> dict:
        return self.repository.agregar_favorito_dto(usuario_id, producto_id)

    def toggle_favorito(self, usuario_id: int, producto_id: int) -> bool:
        return self.repository.toggle_favorito(usuario_id, producto_id)

    def quitar_favorito_dto(self, usuario_id: int, producto_id: int) -> dict | None:
        return self.repository.quitar_favorito_dto(usuario_id, producto_id)


class CarritoLineasService:
    def __init__(self, port: CarritoLineasPort) -> None:
        self._port = port

    def listar_items(self, usuario_id: int) -> list[dict]:
        return self._port.listar_items(usuario_id)

    def agregar_producto(self, usuario_id: int, producto_id: int, cantidad: int) -> list[dict]:
        return self._port.agregar_producto(usuario_id, producto_id, cantidad)

    def actualizar_cantidad(self, usuario_id: int, detalle_id: int, cantidad: int) -> list[dict]:
        return self._port.actualizar_cantidad(usuario_id, detalle_id, cantidad)

    def eliminar_detalle(self, usuario_id: int, detalle_id: int) -> list[dict]:
        return self._port.eliminar_detalle(usuario_id, detalle_id)

    def vaciar(self, usuario_id: int) -> None:
        self._port.vaciar(usuario_id)
