from dataclasses import dataclass


@dataclass(frozen=True)
class AnulacionVentaResultado:
    venta_id: int
    pagos_reembolsados: int
    items_revertidos: int
