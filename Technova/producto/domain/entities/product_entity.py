from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ProductoEntidad:
    id: int | None
    codigo: str
    nombre: str
    proveedor_id: int
    stock: int
    costo_unitario: Decimal
    activo: bool = True
    imagen_url: str = ""
    categoria: str = ""
    marca: str = ""
    color: str = ""
    descripcion: str = ""
    precio_venta: Decimal | None = None
