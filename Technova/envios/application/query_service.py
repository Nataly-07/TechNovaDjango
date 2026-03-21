from envios.domain.query_ports import EnvioQueryPort


class EnvioQueryService:
    def __init__(self, repository: EnvioQueryPort) -> None:
        self.repository = repository

    def listar_envios(self) -> list[dict]:
        return self.repository.listar_envios()

    def listar_transportadoras(self) -> list[dict]:
        return self.repository.listar_transportadoras()

    def crear_transportadora(self, data: dict) -> int:
        return self.repository.crear_transportadora(data)
