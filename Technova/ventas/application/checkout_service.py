from datetime import date
from decimal import Decimal

from ventas.domain.ports import CheckoutPort
from ventas.domain.results import CheckoutResultado


class CheckoutService:
    def __init__(self, checkout_port: CheckoutPort) -> None:
        self.checkout_port = checkout_port

    def ejecutar_checkout(
        self,
        *,
        usuario_id: int,
        carrito_id: int,
        metodo_pago: str,
        numero_factura: str,
        fecha_factura: date,
        transportadora_id: int,
        numero_guia: str,
        costo_envio: Decimal = Decimal("0"),
    ) -> CheckoutResultado:
        return self.checkout_port.ejecutar_checkout(
            usuario_id=usuario_id,
            carrito_id=carrito_id,
            metodo_pago=metodo_pago,
            numero_factura=numero_factura,
            fecha_factura=fecha_factura,
            transportadora_id=transportadora_id,
            numero_guia=numero_guia,
            costo_envio=costo_envio,
        )
