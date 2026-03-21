from abc import ABC, abstractmethod

from .entities import ProductoEntidad


class ProductoRepositoryPort(ABC):
    @abstractmethod
    def obtener_por_id(self, producto_id: int) -> ProductoEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def listar_activos(self) -> list[ProductoEntidad]:
        raise NotImplementedError

    @abstractmethod
    def guardar(self, producto: ProductoEntidad) -> ProductoEntidad:
        raise NotImplementedError
