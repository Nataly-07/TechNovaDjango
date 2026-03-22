from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class ItemCompraEntidad:
    producto_id: int
    cantidad: int
    precio_unitario: Decimal


@dataclass(frozen=True)
class CompraEntidad:
    id: int | None
    usuario_id: int
    proveedor_id: int
    fecha_compra: datetime
    total: Decimal
    estado: str
    items: list[ItemCompraEntidad]
