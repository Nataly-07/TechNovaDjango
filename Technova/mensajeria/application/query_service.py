from mensajeria.domain.query_ports import MensajeriaQueryPort


class MensajeriaQueryService:
    def __init__(self, repository: MensajeriaQueryPort) -> None:
        self.repository = repository

    def listar_notificaciones(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_notificaciones(usuario_id)

    def listar_mensajes_directos(self, usuario_id: int | None) -> list[dict]:
        return self.repository.listar_mensajes_directos(usuario_id)

    def listar_mensajes_empleado(self, empleado_id: int | None) -> list[dict]:
        return self.repository.listar_mensajes_empleado(empleado_id)

    def crear_mensaje_directo(self, data: dict) -> int:
        return self.repository.crear_mensaje_directo(data)

    def crear_mensaje_empleado(self, data: dict) -> int:
        return self.repository.crear_mensaje_empleado(data)
