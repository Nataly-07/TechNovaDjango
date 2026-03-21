from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PagoEntidad:
    id: int | None
    fecha_pago: date
    numero_factura: str
    fecha_factura: date
    monto: Decimal
    estado_pago: str
