from pagos.domain.entities import PagoEntidad
from pagos.domain.repositories import PagoRepositoryPort


class PagoService:
    def __init__(self, repository: PagoRepositoryPort) -> None:
        self.repository = repository

    def registrar_pago(self, pago: PagoEntidad) -> PagoEntidad:
        if pago.monto <= 0:
            raise ValueError("El monto del pago debe ser mayor que cero.")
        if not pago.numero_factura.strip():
            raise ValueError("El numero de factura es obligatorio.")
        return self.repository.guardar(pago)
