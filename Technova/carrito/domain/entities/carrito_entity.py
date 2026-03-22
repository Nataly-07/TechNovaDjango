from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ItemCarritoEntidad:
    producto_id: int
    cantidad: int


@dataclass(frozen=True)
class CarritoEntidad:
    id: int | None
    usuario_id: int
    fecha_creacion: datetime
    estado: str
    items: list[ItemCarritoEntidad]
