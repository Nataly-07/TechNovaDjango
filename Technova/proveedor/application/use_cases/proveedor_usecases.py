from proveedor.domain.entities import ProveedorEntidad
from proveedor.domain.repositories import ProveedorRepositoryPort


class ProveedorService:
    def __init__(self, repository: ProveedorRepositoryPort) -> None:
        self._repository = repository

    def listar_todos(self) -> list[ProveedorEntidad]:
        return self._repository.listar_todos()

    def obtener_por_id(self, proveedor_id: int) -> ProveedorEntidad | None:
        return self._repository.obtener_por_id(proveedor_id)

    def crear(self, entidad: ProveedorEntidad) -> ProveedorEntidad:
        return self._repository.crear(entidad)

    def actualizar(self, entidad: ProveedorEntidad) -> ProveedorEntidad | None:
        return self._repository.actualizar(entidad)

    def eliminar(self, proveedor_id: int) -> bool:
        return self._repository.marcar_inactivo(proveedor_id)

    def cambiar_estado(self, proveedor_id: int, activo: bool) -> ProveedorEntidad | None:
        return self._repository.establecer_activo(proveedor_id, activo)
