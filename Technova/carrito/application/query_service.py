from carrito.domain.query_ports import CarritoQueryPort


class CarritoQueryService:
    def __init__(self, repository: CarritoQueryPort) -> None:
        self.repository = repository

    def listar_carritos(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_carritos(usuario_id)

    def listar_favoritos(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_favoritos(usuario_id)

    def crear_favorito(self, usuario_id: int, producto_id: int) -> int:
        return self.repository.crear_favorito(usuario_id, producto_id)
