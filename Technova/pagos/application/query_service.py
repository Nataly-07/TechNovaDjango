from pagos.domain.query_ports import PagoQueryPort


class PagoQueryService:
    def __init__(self, repository: PagoQueryPort) -> None:
        self.repository = repository

    def listar_pagos(self) -> list[dict]:
        return self.repository.listar_pagos()

    def listar_metodos_usuario(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_metodos_usuario(usuario_id)

    def crear_metodo_usuario(self, data: dict) -> int:
        return self.repository.crear_metodo_usuario(data)
