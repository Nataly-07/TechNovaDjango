from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from venta.domain.results import AnulacionVentaResultado, CheckoutResultado


class CheckoutPort(ABC):
    @abstractmethod
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
        raise NotImplementedError


class VentaAnulacionPort(ABC):
    @abstractmethod
    def anular_venta(self, venta_id: int) -> AnulacionVentaResultado:
        raise NotImplementedError


class VentaQueryPort(ABC):
    @abstractmethod
    def listar_ventas(self) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def obtener_venta(self, venta_id: int) -> dict | None:
        raise NotImplementedError

    @abstractmethod
    def listar_ventas_por_usuario(self, usuario_id: int) -> list[dict]:
        raise NotImplementedError
