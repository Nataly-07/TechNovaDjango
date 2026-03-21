from django.utils import timezone

from pagos.domain.entities import PagoEntidad
from pagos.domain.repositories import PagoRepositoryPort
from pagos.domain.value_objects import EstadoPago
from pagos.models import Pago

from .mappers import PagoMapper


class PagoPersistenceAdapter(PagoRepositoryPort):
    def guardar(self, pago: PagoEntidad) -> PagoEntidad:
        model = Pago.objects.create(
            fecha_pago=pago.fecha_pago,
            numero_factura=pago.numero_factura,
            fecha_factura=pago.fecha_factura,
            monto=pago.monto,
            estado_pago=pago.estado_pago,
        )
        return PagoMapper.to_domain(model)

    def obtener_por_id(self, pago_id: int) -> PagoEntidad | None:
        model = Pago.objects.filter(id=pago_id).first()
        if model is None:
            return None
        return PagoMapper.to_domain(model)

    def actualizar_estado(self, pago_id: int, estado_pago: str) -> PagoEntidad:
        model = Pago.objects.filter(id=pago_id).first()
        if model is None:
            raise ValueError("El pago no existe.")
        model.estado_pago = estado_pago
        if estado_pago == EstadoPago.APROBADO.value:
            model.fecha_pago = timezone.localdate()
            model.save(update_fields=["estado_pago", "fecha_pago", "actualizado_en"])
        else:
            model.save(update_fields=["estado_pago", "actualizado_en"])
        return PagoMapper.to_domain(model)
