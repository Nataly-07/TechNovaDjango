from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class DetalleVentaEntidad:
    producto_id: int
    cantidad: int
    precio_unitario: Decimal


@dataclass(frozen=True)
class VentaEntidad:
    id: int | None
    usuario_id: int
    fecha_venta: date
    estado: str
    total: Decimal
    detalles: list[DetalleVentaEntidad]
