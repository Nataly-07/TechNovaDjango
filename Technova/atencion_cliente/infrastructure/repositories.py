from atencion_cliente.domain.entities import AtencionClienteEntidad
from atencion_cliente.domain.repositories import AtencionClienteRepositoryPort
from atencion_cliente.models import AtencionCliente


class AtencionClienteOrmRepository(AtencionClienteRepositoryPort):
    def guardar(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        model = AtencionCliente.objects.create(
            usuario_id=solicitud.usuario_id,
            fecha_consulta=solicitud.fecha_consulta,
            tema=solicitud.tema,
            descripcion=solicitud.descripcion,
            estado=solicitud.estado,
            respuesta=solicitud.respuesta,
        )
        return AtencionClienteEntidad(
            id=model.id,
            usuario_id=model.usuario_id,
            fecha_consulta=model.fecha_consulta,
            tema=model.tema,
            descripcion=model.descripcion,
            estado=model.estado,
            respuesta=model.respuesta,
        )
