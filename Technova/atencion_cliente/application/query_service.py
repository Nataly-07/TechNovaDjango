from atencion_cliente.domain.query_ports import AtencionQueryPort


class AtencionQueryService:
    def __init__(self, repository: AtencionQueryPort) -> None:
        self.repository = repository

    def listar_solicitudes(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_solicitudes(usuario_id)

    def listar_reclamos(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_reclamos(usuario_id)

    def crear_reclamo(self, data: dict) -> dict:
        return self.repository.crear_reclamo(data)
