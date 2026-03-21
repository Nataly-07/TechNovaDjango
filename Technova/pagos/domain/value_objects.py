from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


@dataclass(frozen=True)
class Dinero:
    valor: Decimal

    @staticmethod
    def crear(valor: Decimal) -> "Dinero":
        if valor <= Decimal("0"):
            raise ValueError("El monto debe ser mayor que cero.")
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


class EstadoPago(StrEnum):
    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    REEMBOLSADO = "reembolsado"

    @staticmethod
    def validar(valor: str) -> "EstadoPago":
        try:
            return EstadoPago(valor)
        except ValueError as exc:
            raise ValueError(f"Estado de pago invalido: {valor}") from exc
