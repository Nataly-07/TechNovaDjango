from abc import ABC, abstractmethod


class OrdenQueryPort(ABC):
    @abstractmethod
    def listar_ordenes(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def obtener_orden(self, orden_id: int) -> dict | None:
        raise NotImplementedError
