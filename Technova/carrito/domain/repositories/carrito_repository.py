from abc import ABC, abstractmethod

from carrito.domain.entities import CarritoEntidad


class CarritoRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, carrito: CarritoEntidad) -> CarritoEntidad:
        raise NotImplementedError
