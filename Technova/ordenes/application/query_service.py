from ordenes.domain.query_ports import OrdenesQueryPort


class OrdenesQueryService:
    def __init__(self, repository: OrdenesQueryPort) -> None:
        self.repository = repository

    def listar_ordenes(self) -> list[dict]:
        return self.repository.listar_ordenes()
