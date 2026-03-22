from abc import ABC, abstractmethod

from orden.domain.entities import OrdenCompraEntidad


class OrdenCompraRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, orden: OrdenCompraEntidad) -> OrdenCompraEntidad:
        raise NotImplementedError

    @abstractmethod
    def actualizar_estado(self, orden_id: int, estado: str) -> bool:
        raise NotImplementedError
