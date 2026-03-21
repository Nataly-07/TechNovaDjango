from django.utils import timezone

from pagos.models import Pago


class PagoStateService:
    allowed_transitions = {
        Pago.EstadoPago.PENDIENTE: {Pago.EstadoPago.APROBADO, Pago.EstadoPago.RECHAZADO},
        Pago.EstadoPago.APROBADO: {Pago.EstadoPago.REEMBOLSADO},
        Pago.EstadoPago.RECHAZADO: {Pago.EstadoPago.PENDIENTE},
        Pago.EstadoPago.REEMBOLSADO: set(),
    }

    def actualizar_estado(self, pago_id: int, nuevo_estado: str) -> Pago:
        pago = Pago.objects.filter(id=pago_id).first()
        if pago is None:
            raise ValueError("El pago no existe.")

        if nuevo_estado == pago.estado_pago:
            return pago

        permitidos = self.allowed_transitions.get(pago.estado_pago, set())
        if nuevo_estado not in permitidos:
            raise ValueError(
                f"Transicion invalida de {pago.estado_pago} a {nuevo_estado}."
            )

        pago.estado_pago = nuevo_estado
        if nuevo_estado == Pago.EstadoPago.APROBADO:
            pago.fecha_pago = timezone.localdate()
        pago.save(update_fields=["estado_pago", "fecha_pago", "actualizado_en"])
        return pago
