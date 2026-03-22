from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Dinero:
    valor: Decimal

    @staticmethod
    def crear(valor: Decimal) -> "Dinero":
        if valor < Decimal("0"):
            raise ValueError("El monto no puede ser negativo.")
        return Dinero(valor=valor)


@dataclass(frozen=True)
class NumeroFactura:
    valor: str

    @staticmethod
    def crear(valor: str) -> "NumeroFactura":
        texto = (valor or "").strip()
        if not texto:
            raise ValueError("El numero de factura es obligatorio.")
        return NumeroFactura(valor=texto)
