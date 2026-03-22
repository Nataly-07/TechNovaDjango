from datetime import date
from decimal import Decimal

from venta.domain.repositories import CheckoutPort, VentaAnulacionPort, VentaQueryPort
from venta.domain.results import AnulacionVentaResultado, CheckoutResultado


class VentaService:
    def __init__(self, anulacion_port: VentaAnulacionPort) -> None:
        self.anulacion_port = anulacion_port

    def anular_venta(self, venta_id: int) -> AnulacionVentaResultado:
        return self.anulacion_port.anular_venta(venta_id)


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


class VentaQueryService:
    def __init__(self, repository: VentaQueryPort) -> None:
        self.repository = repository

    def listar_ventas(self) -> list[dict]:
        return self.repository.listar_ventas()

    def obtener_venta(self, venta_id: int) -> dict | None:
        return self.repository.obtener_venta(venta_id)

    def listar_ventas_por_usuario(self, usuario_id: int) -> list[dict]:
        return self.repository.listar_ventas_por_usuario(usuario_id)
