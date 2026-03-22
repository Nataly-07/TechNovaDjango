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

    @abstractmethod
    def obtener_transportadora(self, transportadora_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def actualizar_transportadora(self, transportadora_id: int, data: dict) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def desactivar_transportadora(self, transportadora_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def listar_transportadoras_por_envio(self, envio_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def obtener_envio(self, envio_id: int) -> dict | None:
        raise NotImplementedError
