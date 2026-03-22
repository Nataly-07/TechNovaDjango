from abc import ABC, abstractmethod


class CarritoLineasPort(ABC):
    @abstractmethod
    def listar_items(self, usuario_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def agregar_producto(self, usuario_id: int, producto_id: int, cantidad: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def actualizar_cantidad(self, usuario_id: int, detalle_id: int, cantidad: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def eliminar_detalle(self, usuario_id: int, detalle_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def vaciar(self, usuario_id: int) -> None:
        raise NotImplementedError
