from pagos.domain.entities import PagoEntidad
from pagos.domain.repositories import PagoRepositoryPort
from pagos.models import Pago


class PagoOrmRepository(PagoRepositoryPort):
    def guardar(self, pago: PagoEntidad) -> PagoEntidad:
        model = Pago.objects.create(
            fecha_pago=pago.fecha_pago,
            numero_factura=pago.numero_factura,
            fecha_factura=pago.fecha_factura,
            monto=pago.monto,
            estado_pago=pago.estado_pago,
        )
        return PagoEntidad(
            id=model.id,
            fecha_pago=model.fecha_pago,
            numero_factura=model.numero_factura,
            fecha_factura=model.fecha_factura,
            monto=model.monto,
            estado_pago=model.estado_pago,
        )
