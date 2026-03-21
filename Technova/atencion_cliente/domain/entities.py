from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AtencionClienteEntidad:
    id: int | None
    usuario_id: int
    fecha_consulta: datetime
    tema: str
    descripcion: str
    estado: str
    respuesta: str = ""
