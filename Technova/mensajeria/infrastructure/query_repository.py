from django.db.models import Q

from mensajeria.domain.query_ports import MensajeriaQueryPort
from mensajeria.models import MensajeDirecto, MensajeEmpleado, Notificacion


class MensajeriaQueryRepository(MensajeriaQueryPort):
    def listar_notificaciones(self, usuario_id: int | None) -> list[dict]:
        queryset = Notificacion.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [
            {
                "id": n.id,
                "usuario_id": n.usuario_id,
                "titulo": n.titulo,
                "mensaje": n.mensaje,
                "tipo": n.tipo,
                "leida": n.leida,
                "fecha_creacion": n.fecha_creacion.isoformat(),
            }
            for n in queryset
        ]

    def listar_mensajes_directos(self, usuario_id: int | None) -> list[dict]:
        queryset = MensajeDirecto.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(
                Q(destinatario_usuario_id=usuario_id) | Q(remitente_usuario_id=usuario_id)
            )
        return [
            {
                "id": m.id,
                "conversacion_id": m.conversacion_id,
                "tipo_remitente": m.tipo_remitente,
                "remitente_usuario_id": m.remitente_usuario_id,
                "destinatario_usuario_id": m.destinatario_usuario_id,
                "asunto": m.asunto,
                "mensaje": m.mensaje,
                "estado": m.estado,
            }
            for m in queryset
        ]

    def listar_mensajes_empleado(self, empleado_id: int | None) -> list[dict]:
        queryset = MensajeEmpleado.objects.order_by("-id")
        if empleado_id:
            queryset = queryset.filter(empleado_usuario_id=empleado_id)
        return [
            {
                "id": m.id,
                "empleado_usuario_id": m.empleado_usuario_id,
                "remitente_usuario_id": m.remitente_usuario_id,
                "asunto": m.asunto,
                "tipo": m.tipo,
                "prioridad": m.prioridad,
                "leido": m.leido,
            }
            for m in queryset
        ]

    def crear_mensaje_directo(self, data: dict) -> int:
        mensaje = MensajeDirecto.objects.create(**data)
        return mensaje.id

    def crear_mensaje_empleado(self, data: dict) -> int:
        mensaje = MensajeEmpleado.objects.create(**data)
        return mensaje.id
