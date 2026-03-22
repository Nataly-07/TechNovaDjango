from atencion_cliente.domain.entities import AtencionClienteEntidad
from atencion_cliente.domain.repositories import AtencionClienteRepositoryPort, AtencionQueryPort


class AtencionClienteService:
    def __init__(self, repository: AtencionClienteRepositoryPort) -> None:
        self.repository = repository

    def crear_solicitud(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        if not solicitud.tema.strip():
            raise ValueError("El tema es obligatorio.")
        if not solicitud.descripcion.strip():
            raise ValueError("La descripcion es obligatoria.")
        return self.repository.guardar(solicitud)


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
