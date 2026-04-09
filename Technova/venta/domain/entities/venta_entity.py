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
    tipo_venta: str
    empleado_id: int | None
    administrador_id: int | None
    fecha_venta: date
    estado: str
    total: Decimal
    detalles: list[DetalleVentaEntidad]
