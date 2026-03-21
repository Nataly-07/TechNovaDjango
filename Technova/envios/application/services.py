from envios.domain.entities import EnvioEntidad
from envios.domain.repositories import EnvioRepositoryPort


class EnvioService:
    def __init__(self, repository: EnvioRepositoryPort) -> None:
        self.repository = repository

    def registrar_envio(self, envio: EnvioEntidad) -> EnvioEntidad:
        if not envio.numero_guia.strip():
            raise ValueError("El numero de guia es obligatorio.")
        return self.repository.guardar(envio)
