from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class ItemOrdenEntidad:
    producto_id: int
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal


@dataclass(frozen=True)
class OrdenCompraEntidad:
    id: int | None
    proveedor_id: int
    fecha: date
    total: Decimal
    estado: str
    items: list[ItemOrdenEntidad]
