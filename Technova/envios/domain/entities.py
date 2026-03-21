from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class EnvioEntidad:
    id: int | None
    venta_id: int
    transportadora_id: int
    fecha_envio: datetime
    numero_guia: str
    costo_envio: Decimal
    estado: str
