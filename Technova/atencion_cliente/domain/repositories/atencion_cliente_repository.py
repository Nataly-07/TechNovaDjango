from abc import ABC, abstractmethod

from atencion_cliente.domain.entities import AtencionClienteEntidad


class AtencionClienteRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        raise NotImplementedError
