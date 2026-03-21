from abc import ABC, abstractmethod

from .entities import CompraEntidad


class CompraRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, compra: CompraEntidad) -> CompraEntidad:
        raise NotImplementedError
