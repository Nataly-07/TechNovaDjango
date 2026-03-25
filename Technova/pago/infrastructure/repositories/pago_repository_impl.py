from django.utils import timezone

from pago.domain.entities import PagoEntidad
from pago.domain.repositories import PagoRepositoryPort
from pago.domain.value_objects import EstadoPago
from pago.infrastructure.mappers import PagoMapper
from pago.models import Pago


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
        estado_anterior = model.estado_pago
        model.estado_pago = estado_pago
        if estado_pago == EstadoPago.APROBADO.value:
            model.fecha_pago = timezone.localdate()
            model.save(update_fields=["estado_pago", "fecha_pago", "actualizado_en"])
        else:
            model.save(update_fields=["estado_pago", "actualizado_en"])
        if (
            estado_pago == EstadoPago.RECHAZADO.value
            and estado_anterior != EstadoPago.RECHAZADO.value
        ):
            from mensajeria.services.notificaciones_admin import notificar_pago_rechazado

            notificar_pago_rechazado(
                pago_id=model.id,
                monto=model.monto,
                numero_factura=model.numero_factura,
            )
        return PagoMapper.to_domain(model)
