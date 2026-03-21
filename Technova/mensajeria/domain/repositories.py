from abc import ABC, abstractmethod

from .entities import NotificacionEntidad


class NotificacionRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, notificacion: NotificacionEntidad) -> NotificacionEntidad:
        raise NotImplementedError
