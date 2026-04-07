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

    def historial_staff_chat(self, empleado_thread_id: int) -> list[dict]:
        return self.repository.historial_staff_chat(empleado_thread_id)

    def resumen_conversaciones_staff_admin(self) -> list[dict]:
        return self.repository.resumen_conversaciones_staff_admin()

    def buscar_empleados_staff_chat(self, query: str, *, limit: int = 40) -> list[dict]:
        return self.repository.buscar_empleados_staff_chat(query, limit=limit)

    def crear_mensaje_staff_chat(
        self,
        *,
        empleado_usuario_id: int,
        remitente_usuario_id: int,
        tipo_remitente: str,
        asunto: str,
        mensaje: str,
        tipo_mensaje: str = "general",
        reclamo_id: int | None = None,
        prioridad: str = "normal",
    ) -> dict | None:
        return self.repository.crear_mensaje_staff_chat(
            empleado_usuario_id=empleado_usuario_id,
            remitente_usuario_id=remitente_usuario_id,
            tipo_remitente=tipo_remitente,
            asunto=asunto,
            mensaje=mensaje,
            tipo_mensaje=tipo_mensaje,
            reclamo_id=reclamo_id,
            prioridad=prioridad,
        )

    def marcar_staff_chat_leido(self, empleado_thread_id: int, lector_id: int, lector_rol: str) -> int:
        return self.repository.marcar_staff_chat_leido(empleado_thread_id, lector_id, lector_rol)

    def detalle_reclamo_staff_chat(self, reclamo_id: int) -> dict | None:
        return self.repository.detalle_reclamo_staff_chat(reclamo_id)

    # ---- Contextos SSR (DTOs listos para templates) ----
    def admin_mensajes_ssr_context(
        self,
        *,
        conversacion_id: int | None,
        marcar_leidos: bool,
        admin_usuario_id: int,
    ) -> dict:
        return self.repository.admin_mensajes_ssr_context(
            conversacion_id=conversacion_id,
            marcar_leidos=marcar_leidos,
            admin_usuario_id=admin_usuario_id,
        )

    def empleado_mensajes_ssr_context(
        self,
        *,
        empleado_id: int,
        conversacion_admin_id: int | None,
        marcar_leidos: bool,
    ) -> dict:
        return self.repository.empleado_mensajes_ssr_context(
            empleado_id=empleado_id,
            conversacion_admin_id=conversacion_admin_id,
            marcar_leidos=marcar_leidos,
        )

    def cliente_mensajes_ssr_context(
        self,
        *,
        usuario_id: int,
        conversacion_id: str | None,
    ) -> dict:
        return self.repository.cliente_mensajes_ssr_context(
            usuario_id=usuario_id,
            conversacion_id=conversacion_id,
        )
