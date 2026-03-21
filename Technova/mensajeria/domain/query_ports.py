from abc import ABC, abstractmethod


class MensajeriaQueryPort(ABC):
    @abstractmethod
    def listar_notificaciones(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_directos(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_empleado(self, empleado_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_mensaje_directo(self, data: dict) -> int:
        raise NotImplementedError

    @abstractmethod
    def crear_mensaje_empleado(self, data: dict) -> int:
        raise NotImplementedError
