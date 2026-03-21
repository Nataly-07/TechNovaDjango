from pagos.domain.entities import PagoEntidad
from pagos.models import Pago


class PagoMapper:
    @staticmethod
    def to_domain(model: Pago) -> PagoEntidad:
        return PagoEntidad(
            id=model.id,
            fecha_pago=model.fecha_pago,
            numero_factura=model.numero_factura,
            fecha_factura=model.fecha_factura,
            monto=model.monto,
            estado_pago=model.estado_pago,
        )
