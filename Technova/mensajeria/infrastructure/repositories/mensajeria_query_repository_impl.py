import uuid
from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from mensajeria.domain.repositories import MensajeriaQueryPort
from mensajeria.models import MensajeDirecto, MensajeEmpleado, Notificacion


class MensajeriaQueryRepository(MensajeriaQueryPort):
    def _notif_dict(self, n: Notificacion) -> dict:
        return {
            "id": n.id,
            "userId": n.usuario_id,
            "usuario_id": n.usuario_id,
            "titulo": n.titulo,
            "mensaje": n.mensaje,
            "tipo": n.tipo,
            "leida": n.leida,
            "fechaCreacion": n.fecha_creacion.isoformat(),
        }

    def listar_notificaciones(self, usuario_id: int | None) -> list[dict]:
        queryset = Notificacion.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [self._notif_dict(n) for n in queryset]

    def listar_notificaciones_todas(self) -> list[dict]:
        return [self._notif_dict(n) for n in Notificacion.objects.order_by("-id")]

    def listar_notificaciones_filtradas(
        self,
        usuario_id: int,
        *,
        solo_no_leidas: bool = False,
        leida: bool | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> list[dict]:
        queryset = Notificacion.objects.filter(usuario_id=usuario_id).order_by("-id")
        if solo_no_leidas:
            queryset = queryset.filter(leida=False)
        if leida is not None:
            queryset = queryset.filter(leida=leida)
        if desde is not None:
            queryset = queryset.filter(fecha_creacion__gte=desde)
        if hasta is not None:
            queryset = queryset.filter(fecha_creacion__lte=hasta)
        return [self._notif_dict(n) for n in queryset]

    def _md_dict(self, m: MensajeDirecto) -> dict:
        return {
            "id": m.id,
            "conversationId": m.conversacion_id,
            "senderId": m.remitente_usuario_id,
            "senderType": m.tipo_remitente,
            "receiverId": m.destinatario_usuario_id,
            "subject": m.asunto,
            "message": m.mensaje,
            "priority": m.prioridad,
            "state": m.estado,
            "isRead": m.leido,
            "createdAt": m.creado_en.isoformat(),
            "parentMessageId": m.mensaje_padre_id,
        }

    def listar_mensajes_directos(self, usuario_id: int | None) -> list[dict]:
        queryset = MensajeDirecto.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(
                Q(destinatario_usuario_id=usuario_id) | Q(remitente_usuario_id=usuario_id)
            )
        return [self._md_dict(m) for m in queryset]

    def listar_mensajes_directos_todos(self) -> list[dict]:
        return [self._md_dict(m) for m in MensajeDirecto.objects.order_by("-id")]

    def listar_mensajes_por_empleado(self, empleado_id: int) -> list[dict]:
        queryset = MensajeDirecto.objects.filter(
            Q(empleado_asignado_id=empleado_id) | Q(destinatario_usuario_id=empleado_id)
        ).order_by("-id")
        return [self._md_dict(m) for m in queryset]

    def listar_mensajes_por_conversacion(self, conversacion_id: str) -> list[dict]:
        return [
            self._md_dict(m)
            for m in MensajeDirecto.objects.filter(conversacion_id=conversacion_id).order_by(
                "creado_en", "id"
            )
        ]

    def obtener_mensaje_directo(self, mensaje_id: int) -> dict | None:
        m = MensajeDirecto.objects.filter(id=mensaje_id).first()
        return self._md_dict(m) if m else None

    def crear_mensaje_directo(self, data: dict) -> int:
        payload = {**data}
        if payload.get("mensaje_padre_id") is None:
            payload.pop("mensaje_padre_id", None)
        mensaje = MensajeDirecto.objects.create(**payload)
        return mensaje.id

    def crear_conversacion_inicial(
        self, usuario_id: int, asunto: str, mensaje: str, prioridad: str
    ) -> dict:
        prioridad_n = (prioridad or "normal").lower()
        if prioridad_n not in {c[0] for c in MensajeDirecto.Prioridad.choices}:
            prioridad_n = MensajeDirecto.Prioridad.NORMAL
        conv = str(uuid.uuid4())
        m = MensajeDirecto.objects.create(
            conversacion_id=conv,
            mensaje_padre=None,
            tipo_remitente=MensajeDirecto.TipoRemitente.CLIENTE,
            remitente_usuario_id=usuario_id,
            destinatario_usuario_id=None,
            asunto=asunto.strip(),
            mensaje=mensaje.strip(),
            prioridad=prioridad_n,
            estado=MensajeDirecto.Estado.ENVIADO,
            leido=False,
        )
        return self._md_dict(m)

    def responder_mensaje_directo(
        self, mensaje_padre_id: int, sender_id: int, sender_type: str, texto: str
    ) -> dict | None:
        padre = MensajeDirecto.objects.filter(id=mensaje_padre_id).first()
        if padre is None:
            return None
        st = sender_type.strip().lower()
        if st == "employee":
            st = "empleado"
        if st == "client":
            st = "cliente"
        if st not in (MensajeDirecto.TipoRemitente.CLIENTE, MensajeDirecto.TipoRemitente.EMPLEADO):
            raise ValueError("senderType debe ser cliente o empleado.")

        if st == MensajeDirecto.TipoRemitente.EMPLEADO:
            dest_id = padre.remitente_usuario_id
        else:
            dest_id = padre.destinatario_usuario_id or padre.empleado_asignado_id

        hijo = MensajeDirecto.objects.create(
            conversacion_id=padre.conversacion_id,
            mensaje_padre=padre,
            tipo_remitente=st,
            remitente_usuario_id=sender_id,
            destinatario_usuario_id=dest_id,
            asunto=padre.asunto,
            mensaje=texto.strip(),
            prioridad=padre.prioridad,
            estado=MensajeDirecto.Estado.ENVIADO,
            empleado_asignado_id=padre.empleado_asignado_id,
            leido=False,
        )
        padre.estado = MensajeDirecto.Estado.RESPONDIDO
        padre.save(update_fields=["estado", "actualizado_en"])
        return self._md_dict(hijo)

    def marcar_mensaje_leido(self, mensaje_id: int) -> dict | None:
        m = MensajeDirecto.objects.filter(id=mensaje_id).first()
        if m is None:
            return None
        m.leido = True
        m.leido_en = timezone.now()
        m.estado = MensajeDirecto.Estado.LEIDO
        m.save(update_fields=["leido", "leido_en", "estado", "actualizado_en"])
        return self._md_dict(m)

    def estadisticas_mensajes_directos(self) -> dict:
        todos = list(MensajeDirecto.objects.order_by("-creado_en"))
        por_conv: dict[str, MensajeDirecto] = {}
        for m in todos:
            if not m.conversacion_id:
                continue
            prev = por_conv.get(m.conversacion_id)
            if prev is None or m.creado_en > prev.creado_en:
                por_conv[m.conversacion_id] = m
        no_leidos = 0
        for ult in por_conv.values():
            es_leido = (
                ult.leido
                or ult.estado == MensajeDirecto.Estado.RESPONDIDO
                or ult.tipo_remitente == MensajeDirecto.TipoRemitente.EMPLEADO
            )
            if not es_leido:
                no_leidos += 1
        return {"mensajes": len(por_conv), "noLeidos": no_leidos}

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

    def crear_mensaje_empleado(self, data: dict) -> int:
        mensaje = MensajeEmpleado.objects.create(**data)
        return mensaje.id
