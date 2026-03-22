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

    @abstractmethod
    def reclamo_a_dict(self, reclamo_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def listar_reclamos_por_estado(self, estado: str) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_reclamo_basico(
        self, usuario_id: int, titulo: str, descripcion: str, prioridad: str
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def responder_reclamo(self, reclamo_id: int, respuesta: str) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def cerrar_reclamo(self, reclamo_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def eliminar_reclamo(self, reclamo_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def enviar_reclamo_al_admin(self, reclamo_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def evaluar_resolucion_reclamo(self, reclamo_id: int, evaluacion: str) -> dict | None:
        raise NotImplementedError
