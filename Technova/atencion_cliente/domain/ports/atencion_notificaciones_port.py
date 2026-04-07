"""Puerto de salida: efectos secundarios de atención al cliente (notificaciones), sin acoplar el caso de uso a Django."""

from abc import ABC, abstractmethod


class NullAtencionNotificaciones:
    """No-op (tests o entornos sin notificaciones)."""

    def on_ticket_creado(self, *, ticket_id: int, cliente_correo: str, tema: str) -> None:
        pass

    def on_respuesta_empleado(
        self,
        *,
        ticket_id: int,
        usuario_cliente_id: int,
        tema: str,
        texto_respuesta: str,
    ) -> None:
        pass

    def on_ticket_cerrado(self, *, ticket_id: int, usuario_cliente_id: int, tema: str) -> None:
        pass


class AtencionNotificacionesPort(ABC):
    """Contrato alineado con TechNovaJavaSpringBoot (notificar staff y cliente)."""

    @abstractmethod
    def on_ticket_creado(self, *, ticket_id: int, cliente_correo: str, tema: str) -> None:
        pass

    @abstractmethod
    def on_respuesta_empleado(
        self,
        *,
        ticket_id: int,
        usuario_cliente_id: int,
        tema: str,
        texto_respuesta: str,
    ) -> None:
        pass

    @abstractmethod
    def on_ticket_cerrado(self, *, ticket_id: int, usuario_cliente_id: int, tema: str) -> None:
        pass
