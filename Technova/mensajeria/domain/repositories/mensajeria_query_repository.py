from abc import ABC, abstractmethod
from datetime import datetime


class MensajeriaQueryPort(ABC):
    @abstractmethod
    def listar_notificaciones(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_notificaciones_todas(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_notificaciones_filtradas(
        self,
        usuario_id: int,
        *,
        solo_no_leidas: bool = False,
        leida: bool | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def marcar_notificacion_leida(self, usuario_id: int, notificacion_id: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    def marcar_todas_notificaciones_leidas(self, usuario_id: int) -> int:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_directos(self, usuario_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_directos_todos(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_por_empleado(self, empleado_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_por_conversacion(self, conversacion_id: str) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def obtener_mensaje_directo(self, mensaje_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def crear_mensaje_directo(self, data: dict) -> int:
        raise NotImplementedError

    @abstractmethod
    def crear_conversacion_inicial(
        self, usuario_id: int, asunto: str, mensaje: str, prioridad: str
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def responder_mensaje_directo(
        self, mensaje_padre_id: int, sender_id: int, sender_type: str, texto: str
    ) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def marcar_mensaje_leido(self, mensaje_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def estadisticas_mensajes_directos(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def listar_mensajes_empleado(self, empleado_id: int | None) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_mensaje_empleado(self, data: dict) -> int:
        raise NotImplementedError

    @abstractmethod
    def historial_staff_chat(self, empleado_thread_id: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def resumen_conversaciones_staff_admin(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def buscar_empleados_staff_chat(self, query: str, *, limit: int) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def crear_mensaje_staff_chat(
        self,
        *,
        empleado_usuario_id: int,
        remitente_usuario_id: int,
        tipo_remitente: str,
        asunto: str,
        mensaje: str,
        tipo_mensaje: str,
        reclamo_id: int | None,
        prioridad: str,
    ) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def marcar_staff_chat_leido(self, empleado_thread_id: int, lector_id: int, lector_rol: str) -> int:
        raise NotImplementedError

    @abstractmethod
    def detalle_reclamo_staff_chat(self, reclamo_id: int) -> dict | None:
        raise NotImplementedError

    # ---- Contextos SSR (Hexagonal estricto: DTOs listos para la capa web) ----
    @abstractmethod
    def admin_mensajes_ssr_context(
        self,
        *,
        conversacion_id: int | None,
        marcar_leidos: bool,
        admin_usuario_id: int,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def empleado_mensajes_ssr_context(
        self,
        *,
        empleado_id: int,
        conversacion_admin_id: int | None,
        marcar_leidos: bool,
    ) -> dict:
        raise NotImplementedError

    @abstractmethod
    def cliente_mensajes_ssr_context(
        self,
        *,
        usuario_id: int,
        conversacion_id: str | None,
    ) -> dict:
        raise NotImplementedError
