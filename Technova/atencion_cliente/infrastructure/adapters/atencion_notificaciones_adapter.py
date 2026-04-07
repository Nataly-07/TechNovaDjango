"""
Adaptador de notificaciones para atención al cliente (infraestructura Django).

Paridad con AtencionClienteServiceImpl (Java): avisar a empleados/admin al crear ticket;
notificar al cliente al responder o cerrar.
"""

from __future__ import annotations

from atencion_cliente.domain.ports.atencion_notificaciones_port import AtencionNotificacionesPort
from mensajeria.models import Notificacion
from usuario.models import Usuario


class AtencionNotificacionesDjango(AtencionNotificacionesPort):
    def on_ticket_creado(self, *, ticket_id: int, cliente_correo: str, tema: str) -> None:
        try:
            titulo = "Nueva Consulta de Cliente"
            mensaje = f"El usuario {cliente_correo} ha abierto un ticket: {tema}"
            tipo = "Atención al Cliente"
            icono = "bx-headphone"
            data = {"ticketId": ticket_id, "tema": tema}
            staff_ids = list(
                Usuario.objects.filter(
                    rol__in=[Usuario.Rol.EMPLEADO, Usuario.Rol.ADMIN],
                    activo=True,
                ).values_list("id", flat=True)
            )
            for uid in staff_ids:
                Notificacion.objects.create(
                    usuario_id=uid,
                    titulo=titulo[:200],
                    mensaje=mensaje,
                    tipo=tipo[:50],
                    icono=icono[:80],
                    leida=False,
                    data_adicional=data,
                )
        except Exception:  # noqa: BLE001 — no bloquear el flujo principal (como en Java)
            pass

    def on_respuesta_empleado(
        self,
        *,
        ticket_id: int,
        usuario_cliente_id: int,
        tema: str,
        texto_respuesta: str,
    ) -> None:
        try:
            frag = texto_respuesta.strip()
            if len(frag) > 100:
                frag = frag[:100] + "..."
            Notificacion.objects.create(
                usuario_id=usuario_cliente_id,
                titulo="Respuesta a tu consulta",
                mensaje=frag,
                tipo="Atención al Cliente"[:50],
                icono="bx-headphone"[:80],
                leida=False,
                data_adicional={"ticketId": ticket_id, "tema": tema},
            )
        except Exception:  # noqa: BLE001
            pass

    def on_ticket_cerrado(self, *, ticket_id: int, usuario_cliente_id: int, tema: str) -> None:
        try:
            raw = tema or "tu consulta"
            tm = raw if len(raw) <= 50 else raw[:50] + "..."
            mensaje = f"Tu consulta sobre '{tm}' ha sido resuelta y cerrada."
            Notificacion.objects.create(
                usuario_id=usuario_cliente_id,
                titulo="Consulta resuelta",
                mensaje=mensaje,
                tipo="Atención al Cliente"[:50],
                icono="bx-headphone"[:80],
                leida=False,
                data_adicional={"ticketId": ticket_id, "tema": tema, "estado": "cerrada"},
            )
        except Exception:  # noqa: BLE001
            pass
