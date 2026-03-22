from proveedor.domain.entities import ProveedorEntidad
from proveedor.domain.repositories import ProveedorRepositoryPort
from proveedor.models import Proveedor


class ProveedorOrmRepository(ProveedorRepositoryPort):
    def _to_entity(self, m: Proveedor) -> ProveedorEntidad:
        return ProveedorEntidad(
            id=m.id,
            identificacion=m.identificacion,
            nombre=m.nombre,
            telefono=m.telefono,
            correo_electronico=m.correo_electronico,
            empresa=m.empresa or "",
            activo=m.activo,
        )

    def listar_todos(self) -> list[ProveedorEntidad]:
        return [self._to_entity(x) for x in Proveedor.objects.order_by("id")]

    def obtener_por_id(self, proveedor_id: int) -> ProveedorEntidad | None:
        try:
            return self._to_entity(Proveedor.objects.get(id=proveedor_id))
        except Proveedor.DoesNotExist:
            return None

    def crear(self, entidad: ProveedorEntidad) -> ProveedorEntidad:
        m = Proveedor.objects.create(
            identificacion=entidad.identificacion,
            nombre=entidad.nombre,
            telefono=entidad.telefono,
            correo_electronico=entidad.correo_electronico,
            empresa=entidad.empresa or "",
            activo=entidad.activo,
        )
        return self._to_entity(m)

    def actualizar(self, entidad: ProveedorEntidad) -> ProveedorEntidad | None:
        if entidad.id is None:
            return None
        try:
            m = Proveedor.objects.get(id=entidad.id)
        except Proveedor.DoesNotExist:
            return None
        m.identificacion = entidad.identificacion
        m.nombre = entidad.nombre
        m.telefono = entidad.telefono
        m.correo_electronico = entidad.correo_electronico
        m.empresa = entidad.empresa or ""
        m.activo = entidad.activo
        m.save()
        return self._to_entity(m)

    def marcar_inactivo(self, proveedor_id: int) -> bool:
        return Proveedor.objects.filter(id=proveedor_id).update(activo=False) > 0

    def establecer_activo(self, proveedor_id: int, activo: bool) -> ProveedorEntidad | None:
        if not Proveedor.objects.filter(id=proveedor_id).update(activo=activo):
            return None
        return self.obtener_por_id(proveedor_id)
