from django.utils import timezone

from atencion_cliente.domain.repositories import AtencionQueryPort
from atencion_cliente.models import AtencionCliente, Reclamo


class AtencionQueryRepository(AtencionQueryPort):
    def listar_solicitudes(self, usuario_id: int | None) -> list[dict]:
        queryset = AtencionCliente.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [
            {
                "id": solicitud.id,
                "usuario_id": solicitud.usuario_id,
                "fecha_consulta": solicitud.fecha_consulta.isoformat(),
                "tema": solicitud.tema,
                "descripcion": solicitud.descripcion,
                "estado": solicitud.estado,
                "respuesta": solicitud.respuesta,
            }
            for solicitud in queryset
        ]

    def _reclamo_dict(self, reclamo: Reclamo) -> dict:
        return {
            "id": reclamo.id,
            "usuarioId": reclamo.usuario_id,
            "usuario_id": reclamo.usuario_id,
            "fechaReclamo": reclamo.fecha_reclamo.isoformat(),
            "fecha_reclamo": reclamo.fecha_reclamo.isoformat(),
            "titulo": reclamo.titulo,
            "descripcion": reclamo.descripcion,
            "estado": reclamo.estado,
            "prioridad": reclamo.prioridad,
            "respuesta": reclamo.respuesta,
            "enviadoAlAdmin": reclamo.enviado_al_admin,
            "evaluacionCliente": reclamo.evaluacion_cliente or None,
        }

    def listar_reclamos(self, usuario_id: int | None) -> list[dict]:
        queryset = Reclamo.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [self._reclamo_dict(r) for r in queryset]

    def crear_reclamo(self, data: dict) -> dict:
        reclamo = Reclamo.objects.create(**data)
        return self._reclamo_dict(reclamo)

    def reclamo_a_dict(self, reclamo_id: int) -> dict | None:
        r = Reclamo.objects.filter(id=reclamo_id).first()
        return self._reclamo_dict(r) if r else None

    def listar_reclamos_por_estado(self, estado: str) -> list[dict]:
        queryset = Reclamo.objects.filter(estado=estado).order_by("-id")
        return [self._reclamo_dict(r) for r in queryset]

    def crear_reclamo_basico(
        self, usuario_id: int, titulo: str, descripcion: str, prioridad: str
    ) -> dict:
        prioridad_norm = (prioridad or "normal").lower()
        valid_p = {c[0] for c in Reclamo.Prioridad.choices}
        if prioridad_norm not in valid_p:
            prioridad_norm = Reclamo.Prioridad.NORMAL
        reclamo = Reclamo.objects.create(
            usuario_id=usuario_id,
            fecha_reclamo=timezone.now(),
            titulo=titulo.strip(),
            descripcion=descripcion.strip(),
            estado=Reclamo.Estado.PENDIENTE,
            prioridad=prioridad_norm,
            respuesta="",
            enviado_al_admin=False,
            evaluacion_cliente="",
        )
        return self._reclamo_dict(reclamo)

    def responder_reclamo(self, reclamo_id: int, respuesta: str) -> dict | None:
        r = Reclamo.objects.filter(id=reclamo_id).first()
        if r is None:
            return None
        r.respuesta = respuesta.strip()
        if r.estado == Reclamo.Estado.PENDIENTE:
            r.estado = Reclamo.Estado.EN_REVISION
        else:
            r.estado = Reclamo.Estado.RESUELTO
        r.save(update_fields=["respuesta", "estado", "actualizado_en"])
        return self._reclamo_dict(r)

    def cerrar_reclamo(self, reclamo_id: int) -> dict | None:
        r = Reclamo.objects.filter(id=reclamo_id).first()
        if r is None:
            return None
        r.estado = Reclamo.Estado.CERRADO
        r.save(update_fields=["estado", "actualizado_en"])
        return self._reclamo_dict(r)

    def eliminar_reclamo(self, reclamo_id: int) -> bool:
        deleted, _ = Reclamo.objects.filter(id=reclamo_id).delete()
        return deleted > 0

    def enviar_reclamo_al_admin(self, reclamo_id: int) -> dict | None:
        r = Reclamo.objects.filter(id=reclamo_id).first()
        if r is None:
            return None
        r.enviado_al_admin = True
        r.estado = Reclamo.Estado.EN_REVISION
        r.save(update_fields=["enviado_al_admin", "estado", "actualizado_en"])
        return self._reclamo_dict(r)

    def evaluar_resolucion_reclamo(self, reclamo_id: int, evaluacion: str) -> dict | None:
        r = Reclamo.objects.filter(id=reclamo_id).first()
        if r is None:
            return None
        ev_raw = evaluacion.strip().lower()
        if ev_raw in ("no_resuelta", "noresuelta", "no") or "no resuel" in ev_raw:
            ev = Reclamo.EvaluacionCliente.NO_RESUELTA
        else:
            ev = Reclamo.EvaluacionCliente.RESUELTA
        r.evaluacion_cliente = ev
        r.save(update_fields=["evaluacion_cliente", "actualizado_en"])
        return self._reclamo_dict(r)
