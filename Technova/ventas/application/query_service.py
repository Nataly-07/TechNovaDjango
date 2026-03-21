from ventas.domain.ports import VentaQueryPort


class VentasQueryService:
    def __init__(self, repository: VentaQueryPort) -> None:
        self.repository = repository

    def listar_ventas(self) -> list[dict]:
        return self.repository.listar_ventas()
