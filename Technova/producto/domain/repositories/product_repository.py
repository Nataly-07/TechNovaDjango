from abc import ABC, abstractmethod
from decimal import Decimal

from producto.domain.entities import ProductoEntidad


class ProductoRepositoryPort(ABC):
    @abstractmethod
    def obtener_por_id(self, producto_id: int) -> ProductoEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def listar_activos(self) -> list[ProductoEntidad]:
        raise NotImplementedError

    @abstractmethod
    def listar_todos(self) -> list[ProductoEntidad]:
        raise NotImplementedError

    @abstractmethod
    def guardar(self, producto: ProductoEntidad) -> ProductoEntidad:
        raise NotImplementedError

    @abstractmethod
    def crear(self, producto: ProductoEntidad) -> ProductoEntidad:
        raise NotImplementedError

    @abstractmethod
    def actualizar_completo(self, producto: ProductoEntidad) -> ProductoEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def marcar_inactivo(self, producto_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def establecer_activo(self, producto_id: int, activo: bool) -> ProductoEntidad | None:
        raise NotImplementedError

    @abstractmethod
    def listar_por_categoria(self, categoria: str) -> list[ProductoEntidad]:
        raise NotImplementedError

    @abstractmethod
    def listar_por_marca(self, marca: str) -> list[ProductoEntidad]:
        raise NotImplementedError

    @abstractmethod
    def buscar_nombre_paginado(
        self, termino: str, page: int, size: int
    ) -> tuple[list[ProductoEntidad], int]:
        raise NotImplementedError

    @abstractmethod
    def listar_rango_precio_paginado(
        self, min_p: Decimal, max_p: Decimal, page: int, size: int
    ) -> tuple[list[ProductoEntidad], int]:
        raise NotImplementedError

    @abstractmethod
    def buscar_avanzado(
        self,
        *,
        termino: str | None,
        marca: str | None,
        categoria: str | None,
        precio_min: Decimal | None,
        precio_max: Decimal | None,
        disponibilidad: str | None,
    ) -> list[ProductoEntidad]:
        raise NotImplementedError
