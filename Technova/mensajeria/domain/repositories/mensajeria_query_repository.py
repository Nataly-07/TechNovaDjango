from abc import ABC, abstractmethod
from datetime import datetime


class MensajeriaQueryPort(ABC):
    @abstractmethod
    def listar_notificaciones(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_notificaciones_todas(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_notificaciones_filtradas(
        self,
        usuario_id: int,
        *,
        solo_no_leidas: bool = False,
        leida: bool | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_directos(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_directos_todos(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_por_empleado(self, empleado_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_por_conversacion(self, conversacion_id: str) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def obtener_mensaje_directo(self, mensaje_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def crear_mensaje_directo(self, data: dict) -> int:
        raise NotImplementedError

    @abstractmethod
    def crear_conversacion_inicial(
        self, usuario_id: int, asunto: str, mensaje: str, prioridad: str
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def responder_mensaje_directo(
        self, mensaje_padre_id: int, sender_id: int, sender_type: str, texto: str
    ) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def marcar_mensaje_leido(self, mensaje_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def estadisticas_mensajes_directos(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_empleado(self, empleado_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_mensaje_empleado(self, data: dict) -> int:
        raise NotImplementedError
