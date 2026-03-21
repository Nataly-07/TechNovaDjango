from abc import ABC, abstractmethod

from .entities import AtencionClienteEntidad


class AtencionClienteRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        raise NotImplementedError
