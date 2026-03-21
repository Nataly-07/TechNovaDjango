from datetime import date

from pagos.domain.entities import PagoEntidad
from pagos.domain.repositories import PagoRepositoryPort
from pagos.domain.value_objects import EstadoPago


class PagoStateService:
    def __init__(self, repository: PagoRepositoryPort) -> None:
        self.repository = repository

    allowed_transitions = {
        EstadoPago.PENDIENTE: {EstadoPago.APROBADO, EstadoPago.RECHAZADO},
        EstadoPago.APROBADO: {EstadoPago.REEMBOLSADO},
        EstadoPago.RECHAZADO: {EstadoPago.PENDIENTE},
        EstadoPago.REEMBOLSADO: set(),
    }

    def actualizar_estado(self, pago_id: int, nuevo_estado: str) -> PagoEntidad:
        pago = self.repository.obtener_por_id(pago_id)
        if pago is None:
            raise ValueError("El pago no existe.")

        nuevo_estado_vo = EstadoPago.validar(nuevo_estado)
        estado_actual_vo = EstadoPago.validar(pago.estado_pago)
        if nuevo_estado_vo == estado_actual_vo:
            return pago

        permitidos = self.allowed_transitions.get(estado_actual_vo, set())
        if nuevo_estado_vo not in permitidos:
            raise ValueError(
                f"Transicion invalida de {pago.estado_pago} a {nuevo_estado}."
            )

        actualizado = self.repository.actualizar_estado(pago_id=pago.id, estado_pago=nuevo_estado_vo.value)
        if nuevo_estado_vo == EstadoPago.APROBADO:
            return PagoEntidad(
                id=actualizado.id,
                fecha_pago=date.today(),
                numero_factura=actualizado.numero_factura,
                fecha_factura=actualizado.fecha_factura,
                monto=actualizado.monto,
                estado_pago=actualizado.estado_pago,
            )
        return actualizado
