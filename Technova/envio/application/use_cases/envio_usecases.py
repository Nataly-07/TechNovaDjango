from envio.domain.entities import EnvioEntidad
from envio.domain.repositories import EnvioQueryPort, EnvioRepositoryPort


class EnvioService:
    def __init__(self, repository: EnvioRepositoryPort) -> None:
        self.repository = repository

    def registrar_envio(self, envio: EnvioEntidad) -> EnvioEntidad:
        if not envio.numero_guia.strip():
            raise ValueError("El numero de guia es obligatorio.")
        return self.repository.guardar(envio)

    def actualizar_envio(self, envio: EnvioEntidad) -> EnvioEntidad:
        if envio.id is None:
            raise ValueError("El envio debe tener id para actualizar.")
        if not envio.numero_guia.strip():
            raise ValueError("El numero de guia es obligatorio.")
        actualizado = self.repository.actualizar(envio)
        if actualizado is None:
            raise ValueError("Envio no encontrado.")
        return actualizado

    def eliminar_envio(self, envio_id: int) -> bool:
        return self.repository.marcar_inactivo(envio_id)


class EnvioQueryService:
    def __init__(self, repository: EnvioQueryPort) -> None:
        self.repository = repository

    def listar_envios(self) -> list[dict]:
        return self.repository.listar_envios()

    def listar_transportadoras(self) -> list[dict]:
        return self.repository.listar_transportadoras()

    def crear_transportadora(self, data: dict) -> int:
        return self.repository.crear_transportadora(data)

    def obtener_transportadora(self, transportadora_id: int) -> dict | None:
        return self.repository.obtener_transportadora(transportadora_id)

    def actualizar_transportadora(self, transportadora_id: int, data: dict) -> dict | None:
        return self.repository.actualizar_transportadora(transportadora_id, data)

    def desactivar_transportadora(self, transportadora_id: int) -> bool:
        return self.repository.desactivar_transportadora(transportadora_id)

    def listar_transportadoras_por_envio(self, envio_id: int) -> list[dict]:
        return self.repository.listar_transportadoras_por_envio(envio_id)

    def obtener_envio(self, envio_id: int) -> dict | None:
        return self.repository.obtener_envio(envio_id)
