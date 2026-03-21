from abc import ABC, abstractmethod

from .entities import CarritoEntidad


class CarritoRepositoryPort(ABC):
    @abstractmethod
    def guardar(self, carrito: CarritoEntidad) -> CarritoEntidad:
        raise NotImplementedError
