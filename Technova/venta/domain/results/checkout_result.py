from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CheckoutResultado:
    venta_id: int
    pago_id: int
    envio_id: int
    total: Decimal
    idempotente: bool = False
