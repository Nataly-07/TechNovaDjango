from abc import ABC, abstractmethod

from pago.domain.entities import PagoEntidad


class PagoRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, pago: PagoEntidad) -> PagoEntidad:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id(self, pago_id: int) -> PagoEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def actualizar_estado(self, pago_id: int, estado_pago: str) -> PagoEntidad:
        raise NotImplementedError
