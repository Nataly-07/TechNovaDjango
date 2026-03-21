from abc import ABC, abstractmethod

from .entities import OrdenCompraEntidad


class OrdenCompraRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, orden: OrdenCompraEntidad) -> OrdenCompraEntidad:
        raise NotImplementedError
