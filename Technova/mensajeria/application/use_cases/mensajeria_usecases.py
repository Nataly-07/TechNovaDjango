from datetime import datetime

from mensajeria.domain.entities import NotificacionEntidad
from mensajeria.domain.repositories import MensajeriaQueryPort, NotificacionRepositoryPort


class NotificacionService:
    def __init__(self, repository: NotificacionRepositoryPort) -> None:
        self.repository = repository

    def crear_notificacion(self, notificacion: NotificacionEntidad) -> NotificacionEntidad:
        if not notificacion.titulo.strip():
            raise ValueError("El titulo de la notificacion es obligatorio.")
        return self.repository.guardar(notificacion)


class MensajeriaQueryService:
    def __init__(self, repository: MensajeriaQueryPort) -> None:
        self.repository = repository

    def listar_notificaciones(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_notificaciones(usuario_id)

    def listar_notificaciones_todas(self) -> list[dict]:
        return self.repository.listar_notificaciones_todas()

    def listar_notificaciones_filtradas(
        self,
        usuario_id: int,
        *,
        solo_no_leidas: bool = False,
        leida: bool | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[dict]:
        return self.repository.listar_notificaciones_filtradas(
            usuario_id,
            solo_no_leidas=solo_no_leidas,
            leida=leida,
            desde=desde,
            hasta=hasta,
        )

    def listar_mensajes_directos(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_mensajes_directos(usuario_id)

    def listar_mensajes_directos_todos(self) -> list[dict]:
        return self.repository.listar_mensajes_directos_todos()

    def listar_mensajes_por_empleado(self, empleado_id: int) -> list[dict]:
        return self.repository.listar_mensajes_por_empleado(empleado_id)

    def listar_mensajes_por_conversacion(self, conversacion_id: str) -> list[dict]:
        return self.repository.listar_mensajes_por_conversacion(conversacion_id)

    def obtener_mensaje_directo(self, mensaje_id: int) -> dict | None:
        return self.repository.obtener_mensaje_directo(mensaje_id)

    def crear_mensaje_directo(self, data: dict) -> int:
        return self.repository.crear_mensaje_directo(data)

    def crear_conversacion_inicial(
        self, usuario_id: int, asunto: str, mensaje: str, prioridad: str
    ) -> dict:
        return self.repository.crear_conversacion_inicial(usuario_id, asunto, mensaje, prioridad)

    def responder_mensaje_directo(
        self, mensaje_padre_id: int, sender_id: int, sender_type: str, texto: str
    ) -> dict | None:
        return self.repository.responder_mensaje_directo(
            mensaje_padre_id, sender_id, sender_type, texto
        )

    def marcar_mensaje_leido(self, mensaje_id: int) -> dict | None:
        return self.repository.marcar_mensaje_leido(mensaje_id)

    def estadisticas_mensajes_directos(self) -> dict:
        return self.repository.estadisticas_mensajes_directos()

    def listar_mensajes_empleado(self, empleado_id: int | None) -> list[dict]:
        return self.repository.listar_mensajes_empleado(empleado_id)

    def crear_mensaje_empleado(self, data: dict) -> int:
        return self.repository.crear_mensaje_empleado(data)
