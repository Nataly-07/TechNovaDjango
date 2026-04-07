from django.utils import timezone

from atencion_cliente.domain.repositories import AtencionQueryPort
from atencion_cliente.models import AtencionCliente, Reclamo
from usuario.models import Usuario


class AtencionQueryRepository(AtencionQueryPort):
    def listar_solicitudes(self, usuario_id: int | None) -> list[dict]:
        queryset = AtencionCliente.objects.select_related("usuario").order_by(
            "-fecha_consulta", "-id"
        )
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [
            {
                "id": solicitud.id,
                "usuario_id": solicitud.usuario_id,
                "usuarioId": solicitud.usuario_id,
                "emailUsuario": getattr(solicitud.usuario, "correo_electronico", "") or "",
                "fecha_consulta": solicitud.fecha_consulta.isoformat(),
                "fechaConsulta": solicitud.fecha_consulta.isoformat(),
                "tema": solicitud.tema,
                "descripcion": solicitud.descripcion,
                "estado": solicitud.estado,
                "respuesta": solicitud.respuesta or "",
            }
            for solicitud in queryset
        ]

    def _reclamo_dict(self, reclamo: Reclamo) -> dict:
        emp = getattr(reclamo, "empleado_asignado", None)
        emp_id = getattr(reclamo, "empleado_asignado_id", None)
        emp_nombre = ""
        if emp is not None:
            emp_nombre = f"{emp.nombres or ''} {emp.apellidos or ''}".strip()
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
            "empleadoAsignadoId": emp_id,
            "empleado_asignado_id": emp_id,
            "empleadoAsignadoNombre": emp_nombre or None,
        }

    def listar_reclamos(self, usuario_id: int | None) -> list[dict]:
        queryset = (
            Reclamo.objects.select_related("usuario", "empleado_asignado")
            .order_by("-fecha_reclamo", "-id")
        )
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [self._reclamo_dict(r) for r in queryset]

    def crear_reclamo(self, data: dict) -> dict:
        reclamo = Reclamo.objects.create(**data)
        return self._reclamo_dict(reclamo)

    def reclamo_a_dict(self, reclamo_id: int) -> dict | None:
        r = (
            Reclamo.objects.select_related("usuario", "empleado_asignado")
            .filter(id=reclamo_id)
            .first()
        )
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

    def asignar_reclamo_a_empleado(self, reclamo_id: int, empleado_usuario_id: int) -> dict | None:
        r = Reclamo.objects.filter(id=reclamo_id).first()
        if r is None:
            return None
        emp = Usuario.objects.filter(pk=empleado_usuario_id, rol=Usuario.Rol.EMPLEADO).first()
        if emp is None:
            return None
        r.empleado_asignado_id = empleado_usuario_id
        if r.estado == Reclamo.Estado.PENDIENTE:
            r.estado = Reclamo.Estado.EN_REVISION
        r.save(update_fields=["empleado_asignado_id", "estado", "actualizado_en"])
        return self.reclamo_a_dict(reclamo_id)
