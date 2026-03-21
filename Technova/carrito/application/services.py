from carrito.domain.entities import CarritoEntidad
from carrito.domain.repositories import CarritoRepositoryPort


class CarritoService:
    def __init__(self, repository: CarritoRepositoryPort) -> None:
        self.repository = repository

    def crear_carrito(self, carrito: CarritoEntidad) -> CarritoEntidad:
        if not carrito.items:
            raise ValueError("El carrito debe tener al menos un item.")
        for item in carrito.items:
            if item.cantidad <= 0:
                raise ValueError("La cantidad de cada item debe ser mayor a cero.")
        return self.repository.guardar(carrito)
