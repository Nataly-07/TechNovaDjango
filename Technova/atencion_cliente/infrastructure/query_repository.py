from atencion_cliente.models import Reclamo
from atencion_cliente.domain.query_ports import AtencionQueryPort


class AtencionQueryRepository(AtencionQueryPort):
    def listar_solicitudes(self, usuario_id: int | None) -> list[dict]:
        from atencion_cliente.models import AtencionCliente

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

    def listar_reclamos(self, usuario_id: int | None) -> list[dict]:
        queryset = Reclamo.objects.order_by("-id")
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)
        return [
            {
                "id": reclamo.id,
                "usuario_id": reclamo.usuario_id,
                "fecha_reclamo": reclamo.fecha_reclamo.isoformat(),
                "titulo": reclamo.titulo,
                "descripcion": reclamo.descripcion,
                "estado": reclamo.estado,
                "prioridad": reclamo.prioridad,
            }
            for reclamo in queryset
        ]

    def crear_reclamo(self, data: dict) -> dict:
        reclamo = Reclamo.objects.create(**data)
        return {"id": reclamo.id, "estado": reclamo.estado}
