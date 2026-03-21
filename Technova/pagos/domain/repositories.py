from abc import ABC, abstractmethod

from .entities import PagoEntidad


class PagoRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, pago: PagoEntidad) -> PagoEntidad:
        raise NotImplementedError
