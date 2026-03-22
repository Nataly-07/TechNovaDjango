from dataclasses import dataclass


@dataclass(frozen=True)
class UsuarioEntidad:
    """Proyeccion minima del usuario en dominio (el ORM sigue siendo la fuente en persistencia)."""

    id: int
    nombre_usuario: str
    correo_electronico: str
    nombres: str
    apellidos: str
    rol: str
    activo: bool
