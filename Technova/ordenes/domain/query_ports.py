from abc import ABC, abstractmethod


class OrdenesQueryPort(ABC):
    @abstractmethod
    def listar_ordenes(self) -> list[dict]:
        raise NotImplementedError
