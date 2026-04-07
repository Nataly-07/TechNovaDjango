from abc import ABC, abstractmethod

from atencion_cliente.domain.entities import AtencionClienteEntidad


class AtencionClienteRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id(self, ticket_id: int) -> AtencionClienteEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def actualizar(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        raise NotImplementedError

    @abstractmethod
    def eliminar(self, ticket_id: int) -> bool:
        raise NotImplementedError
