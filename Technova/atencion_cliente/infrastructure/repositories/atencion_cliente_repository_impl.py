from atencion_cliente.domain.entities import AtencionClienteEntidad
from atencion_cliente.domain.repositories import AtencionClienteRepositoryPort
from atencion_cliente.models import AtencionCliente


class AtencionClienteOrmRepository(AtencionClienteRepositoryPort):
    def _to_entidad(self, model: AtencionCliente) -> AtencionClienteEntidad:
        return AtencionClienteEntidad(
            id=model.id,
            usuario_id=model.usuario_id,
            fecha_consulta=model.fecha_consulta,
            tema=model.tema,
            descripcion=model.descripcion,
            estado=model.estado,
            respuesta=model.respuesta or "",
        )

    def guardar(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        model = AtencionCliente.objects.create(
            usuario_id=solicitud.usuario_id,
            fecha_consulta=solicitud.fecha_consulta,
            tema=solicitud.tema,
            descripcion=solicitud.descripcion,
            estado=solicitud.estado,
            respuesta=solicitud.respuesta or "",
        )
        return self._to_entidad(model)

    def obtener_por_id(self, ticket_id: int) -> AtencionClienteEntidad | None:
        model = AtencionCliente.objects.filter(id=ticket_id).first()
        return self._to_entidad(model) if model else None

    def actualizar(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        if solicitud.id is None:
            raise ValueError("La solicitud debe tener id para actualizar.")
        model = AtencionCliente.objects.get(pk=solicitud.id)
        model.tema = solicitud.tema
        model.descripcion = solicitud.descripcion
        model.estado = solicitud.estado
        model.respuesta = solicitud.respuesta or ""
        model.save(update_fields=["tema", "descripcion", "estado", "respuesta", "actualizado_en"])
        return self._to_entidad(model)

    def eliminar(self, ticket_id: int) -> bool:
        deleted, _ = AtencionCliente.objects.filter(id=ticket_id).delete()
        return deleted > 0
