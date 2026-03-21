from pagos.domain.entities import PagoEntidad
from pagos.domain.repositories import PagoRepositoryPort
from pagos.domain.value_objects import Dinero, EstadoPago, NumeroFactura


class PagoService:
    def __init__(self, repository: PagoRepositoryPort) -> None:
        self.repository = repository

    def registrar_pago(self, pago: PagoEntidad) -> PagoEntidad:
        NumeroFactura.crear(pago.numero_factura)
        Dinero.crear(pago.monto)
        EstadoPago.validar(pago.estado_pago)
        return self.repository.guardar(pago)
