from abc import ABC, abstractmethod

from mensajeria.domain.entities import NotificacionEntidad


class NotificacionRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, notificacion: NotificacionEntidad) -> NotificacionEntidad:
        raise NotImplementedError
