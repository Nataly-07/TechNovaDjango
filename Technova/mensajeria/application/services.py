from mensajeria.domain.entities import NotificacionEntidad
from mensajeria.domain.repositories import NotificacionRepositoryPort


class NotificacionService:
    def __init__(self, repository: NotificacionRepositoryPort) -> None:
        self.repository = repository

    def crear_notificacion(self, notificacion: NotificacionEntidad) -> NotificacionEntidad:
        if not notificacion.titulo.strip():
            raise ValueError("El titulo de la notificacion es obligatorio.")
        return self.repository.guardar(notificacion)
