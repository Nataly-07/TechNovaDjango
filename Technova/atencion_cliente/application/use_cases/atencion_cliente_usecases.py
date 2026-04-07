"""
Casos de uso — Atención al cliente (tickets de consulta).

Reglas alineadas con `AtencionClienteServiceImpl` (TechNovaJavaSpringBoot):
validación de usuario activo, estados abierta → en_proceso al responder, cerrada al cerrar,
notificaciones a staff (nuevo ticket) y al cliente (respuesta / cierre).
"""

from __future__ import annotations

from dataclasses import replace

from atencion_cliente.domain.entities import AtencionClienteEntidad
from atencion_cliente.domain.ports.atencion_notificaciones_port import (
    AtencionNotificacionesPort,
    NullAtencionNotificaciones,
)
from atencion_cliente.domain.repositories import AtencionClienteRepositoryPort, AtencionQueryPort
from atencion_cliente.models import AtencionCliente
from usuario.models import Usuario


class AtencionClienteService:
    def __init__(
        self,
        repository: AtencionClienteRepositoryPort,
        *,
        notificaciones: AtencionNotificacionesPort | None = None,
    ) -> None:
        self.repository = repository
        self._notif = notificaciones or NullAtencionNotificaciones()

    def crear_solicitud(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        if not solicitud.tema.strip():
            raise ValueError("El tema es obligatorio.")
        if not solicitud.descripcion.strip():
            raise ValueError("La descripcion es obligatoria.")

        u = (
            Usuario.objects.filter(pk=solicitud.usuario_id, activo=True)
            .only("id", "correo_electronico")
            .first()
        )
        if not u:
            raise ValueError("Usuario no encontrado o inactivo.")

        validos = {c[0] for c in AtencionCliente.Estado.choices}
        estado_ini = (solicitud.estado or AtencionCliente.Estado.ABIERTA).strip().lower()
        if estado_ini not in validos:
            estado_ini = AtencionCliente.Estado.ABIERTA

        to_save = replace(
            solicitud,
            tema=solicitud.tema.strip(),
            descripcion=solicitud.descripcion.strip(),
            estado=estado_ini,
            respuesta=(solicitud.respuesta or "").strip(),
        )
        guardada = self.repository.guardar(to_save)
        if guardada.id is not None:
            self._notif.on_ticket_creado(
                ticket_id=guardada.id,
                cliente_correo=u.correo_electronico,
                tema=guardada.tema,
            )
        return guardada

    def obtener_ticket(self, ticket_id: int) -> AtencionClienteEntidad | None:
        return self.repository.obtener_por_id(ticket_id)

    def responder_ticket(self, ticket_id: int, respuesta: str) -> AtencionClienteEntidad:
        texto = (respuesta or "").strip()
        if not texto:
            raise ValueError("La respuesta no puede estar vacía.")
        ent = self.repository.obtener_por_id(ticket_id)
        if ent is None:
            raise ValueError("Ticket no encontrado.")
        nuevo_estado = (
            AtencionCliente.Estado.EN_PROCESO
            if ent.estado == AtencionCliente.Estado.ABIERTA
            else ent.estado
        )
        actualizado = replace(ent, respuesta=texto, estado=nuevo_estado)
        saved = self.repository.actualizar(actualizado)
        self._notif.on_respuesta_empleado(
            ticket_id=saved.id or ticket_id,
            usuario_cliente_id=saved.usuario_id,
            tema=saved.tema,
            texto_respuesta=texto,
        )
        return saved

    def cerrar_ticket(self, ticket_id: int) -> AtencionClienteEntidad:
        ent = self.repository.obtener_por_id(ticket_id)
        if ent is None:
            raise ValueError("Ticket no encontrado.")
        saved = self.repository.actualizar(replace(ent, estado=AtencionCliente.Estado.CERRADA))
        self._notif.on_ticket_cerrado(
            ticket_id=saved.id or ticket_id,
            usuario_cliente_id=saved.usuario_id,
            tema=saved.tema,
        )
        return saved

    def eliminar_ticket(self, ticket_id: int) -> bool:
        return self.repository.eliminar(ticket_id)


class AtencionQueryService:
    def __init__(self, repository: AtencionQueryPort) -> None:
        self.repository = repository

    def listar_solicitudes(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_solicitudes(usuario_id)

    def listar_reclamos(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_reclamos(usuario_id)

    def crear_reclamo(self, data: dict) -> dict:
        return self.repository.crear_reclamo(data)

    def reclamo_a_dict(self, reclamo_id: int) -> dict | None:
        return self.repository.reclamo_a_dict(reclamo_id)

    def listar_reclamos_por_estado(self, estado: str) -> list[dict]:
        return self.repository.listar_reclamos_por_estado(estado)

    def crear_reclamo_basico(
        self, usuario_id: int, titulo: str, descripcion: str, prioridad: str
    ) -> dict:
        return self.repository.crear_reclamo_basico(usuario_id, titulo, descripcion, prioridad)

    def responder_reclamo(self, reclamo_id: int, respuesta: str) -> dict | None:
        return self.repository.responder_reclamo(reclamo_id, respuesta)

    def cerrar_reclamo(self, reclamo_id: int) -> dict | None:
        return self.repository.cerrar_reclamo(reclamo_id)

    def eliminar_reclamo(self, reclamo_id: int) -> bool:
        return self.repository.eliminar_reclamo(reclamo_id)

    def enviar_reclamo_al_admin(self, reclamo_id: int) -> dict | None:
        return self.repository.enviar_reclamo_al_admin(reclamo_id)

    def evaluar_resolucion_reclamo(self, reclamo_id: int, evaluacion: str) -> dict | None:
        return self.repository.evaluar_resolucion_reclamo(reclamo_id, evaluacion)

    def asignar_reclamo_a_empleado(
        self,
        reclamo_id: int,
        empleado_usuario_id: int,
        *,
        admin_usuario_id: int,
    ) -> dict | None:
        row = self.repository.asignar_reclamo_a_empleado(reclamo_id, empleado_usuario_id)
        if row is None:
            return None
        from common.container import get_mensajeria_query_service
        from mensajeria.infrastructure.realtime_mensajes import broadcast_mensajes_event

        svc = get_mensajeria_query_service()
        asunto = f"RECLAMO #{reclamo_id}"
        titulo = (row.get("titulo") or "").strip()
        texto = (
            f"Se te asignó el reclamo #{reclamo_id}"
            + (f": «{titulo}»" if titulo else "")
            + ". Revisa el contexto en Mensajes y en Atención al cliente."
        )
        msg = svc.crear_mensaje_staff_chat(
            empleado_usuario_id=empleado_usuario_id,
            remitente_usuario_id=admin_usuario_id,
            tipo_remitente="admin",
            asunto=asunto,
            mensaje=texto,
            tipo_mensaje="reclamo",
            reclamo_id=reclamo_id,
            prioridad="normal",
        )
        if msg:
            broadcast_mensajes_event(empleado_usuario_id, {"event": "new_message", "message": msg})
        return row
