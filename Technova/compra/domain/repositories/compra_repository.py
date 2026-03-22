from abc import ABC, abstractmethod

from compra.domain.entities import CompraEntidad


class CompraRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, compra: CompraEntidad) -> CompraEntidad:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id(self, compra_id: int) -> CompraEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def listar_todas(self) -> list[CompraEntidad]:
        raise NotImplementedError

    @abstractmethod
    def listar_por_usuario(self, usuario_id: int) -> list[CompraEntidad]:
        raise NotImplementedError

    @abstractmethod
    def actualizar_estado(self, compra_id: int, estado: str) -> bool:
        raise NotImplementedError
