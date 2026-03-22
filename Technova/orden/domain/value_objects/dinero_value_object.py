from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Dinero:
    valor: Decimal

    @staticmethod
    def crear(valor: Decimal) -> "Dinero":
        if valor < Decimal("0"):
            raise ValueError("El valor monetario no puede ser negativo.")
        return Dinero(valor=valor)
