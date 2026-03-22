from abc import ABC, abstractmethod

from proveedor.domain.entities import ProveedorEntidad


class ProveedorRepositoryPort(ABC):
    @abstractmethod
    def listar_todos(self) -> list[ProveedorEntidad]:
        raise NotImplementedError

    @abstractmethod
    def obtener_por_id(self, proveedor_id: int) -> ProveedorEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def crear(self, entidad: ProveedorEntidad) -> ProveedorEntidad:
        raise NotImplementedError

    @abstractmethod
    def actualizar(self, entidad: ProveedorEntidad) -> ProveedorEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def marcar_inactivo(self, proveedor_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def establecer_activo(self, proveedor_id: int, activo: bool) -> ProveedorEntidad | None:
        raise NotImplementedError
