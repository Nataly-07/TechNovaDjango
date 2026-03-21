from atencion_cliente.domain.entities import AtencionClienteEntidad
from atencion_cliente.domain.repositories import AtencionClienteRepositoryPort


class AtencionClienteService:
    def __init__(self, repository: AtencionClienteRepositoryPort) -> None:
        self.repository = repository

    def crear_solicitud(self, solicitud: AtencionClienteEntidad) -> AtencionClienteEntidad:
        if not solicitud.tema.strip():
            raise ValueError("El tema es obligatorio.")
        if not solicitud.descripcion.strip():
            raise ValueError("La descripcion es obligatoria.")
        return self.repository.guardar(solicitud)
