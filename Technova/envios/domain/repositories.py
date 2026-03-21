from abc import ABC, abstractmethod

from .entities import EnvioEntidad


class EnvioRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, envio: EnvioEntidad) -> EnvioEntidad:
        raise NotImplementedError
