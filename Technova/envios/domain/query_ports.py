from abc import ABC, abstractmethod


class EnvioQueryPort(ABC):
    @abstractmethod
    def listar_envios(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_transportadoras(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_transportadora(self, data: dict) -> int:
        raise NotImplementedError
