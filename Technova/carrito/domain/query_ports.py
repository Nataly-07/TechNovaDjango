from abc import ABC, abstractmethod


class CarritoQueryPort(ABC):
    @abstractmethod
    def listar_carritos(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_favoritos(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_favorito(self, usuario_id: int, producto_id: int) -> int:
        raise NotImplementedError
