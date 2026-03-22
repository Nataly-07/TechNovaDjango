from dataclasses import dataclass


@dataclass(frozen=True)
class ProveedorEntidad:
    id: int | None
    identificacion: str
    nombre: str
    telefono: str
    correo_electronico: str
    empresa: str
    activo: bool = True
