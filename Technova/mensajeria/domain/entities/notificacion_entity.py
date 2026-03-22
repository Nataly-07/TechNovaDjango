from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NotificacionEntidad:
    id: int | None
    usuario_id: int
    titulo: str
    mensaje: str
    tipo: str
    icono: str
    leida: bool
    fecha_creacion: datetime
