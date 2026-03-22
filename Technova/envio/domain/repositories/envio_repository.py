from abc import ABC, abstractmethod

from envio.domain.entities import EnvioEntidad


class EnvioRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, envio: EnvioEntidad) -> EnvioEntidad:
        raise NotImplementedError

    @abstractmethod
    def actualizar(self, envio: EnvioEntidad) -> EnvioEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def marcar_inactivo(self, envio_id: int) -> bool:
        raise NotImplementedError
