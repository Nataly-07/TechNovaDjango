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

    @abstractmethod
    def eliminar_favorito(self, usuario_id: int, producto_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def listar_favoritos_todos_dto(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_favoritos_usuario_dto(self, usuario_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def agregar_favorito_dto(self, usuario_id: int, producto_id: int) -> dict:
        raise NotImplementedError

    @abstractmethod
    def toggle_favorito(self, usuario_id: int, producto_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def quitar_favorito_dto(self, usuario_id: int, producto_id: int) -> dict | None:
        raise NotImplementedError
