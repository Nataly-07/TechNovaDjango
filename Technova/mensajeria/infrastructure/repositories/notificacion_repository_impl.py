from mensajeria.domain.entities import NotificacionEntidad
from mensajeria.domain.repositories import NotificacionRepositoryPort
from mensajeria.models import Notificacion


class NotificacionOrmRepository(NotificacionRepositoryPort):
    def guardar(self, notificacion: NotificacionEntidad) -> NotificacionEntidad:
        model = Notificacion.objects.create(
            usuario_id=notificacion.usuario_id,
            titulo=notificacion.titulo,
            mensaje=notificacion.mensaje,
            tipo=notificacion.tipo,
            icono=notificacion.icono,
            leida=notificacion.leida,
            fecha_creacion=notificacion.fecha_creacion,
        )
        return NotificacionEntidad(
            id=model.id,
            usuario_id=model.usuario_id,
            titulo=model.titulo,
            mensaje=model.mensaje,
            tipo=model.tipo,
            icono=model.icono,
            leida=model.leida,
            fecha_creacion=model.fecha_creacion,
        )
