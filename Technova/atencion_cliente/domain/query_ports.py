from abc import ABC, abstractmethod


class AtencionQueryPort(ABC):
    @abstractmethod
    def listar_solicitudes(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_reclamos(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_reclamo(self, data: dict) -> dict:
        raise NotImplementedError
