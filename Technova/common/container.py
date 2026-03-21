from atencion_cliente.application.query_service import AtencionQueryService
from atencion_cliente.application.services import AtencionClienteService
from atencion_cliente.infrastructure.query_repository import AtencionQueryRepository
from atencion_cliente.infrastructure.repositories import AtencionClienteOrmRepository
from carrito.application.query_service import CarritoQueryService
from carrito.application.services import CarritoService
from carrito.infrastructure.query_repository import CarritoQueryRepository
from carrito.infrastructure.repositories import CarritoOrmRepository
from compras.application.services import CompraService
from compras.infrastructure.repositories import CompraOrmRepository
from envios.application.query_service import EnvioQueryService
from envios.application.services import EnvioService
from envios.infrastructure.query_repository import EnvioQueryRepository
from envios.infrastructure.repositories import EnvioOrmRepository
from mensajeria.application.query_service import MensajeriaQueryService
from mensajeria.application.services import NotificacionService
from mensajeria.infrastructure.query_repository import MensajeriaQueryRepository
from mensajeria.infrastructure.repositories import NotificacionOrmRepository
from ordenes.application.query_service import OrdenesQueryService
from ordenes.application.services import OrdenCompraService
from ordenes.infrastructure.query_repository import OrdenesQueryRepository
from ordenes.infrastructure.persistence.repository_adapter import OrdenPersistenceAdapter
from pagos.application.payment_state_service import PagoStateService
from pagos.application.query_service import PagoQueryService
from pagos.application.services import PagoService
from pagos.infrastructure.query_repository import PagoQueryRepository
from pagos.infrastructure.persistence.repository_adapter import PagoPersistenceAdapter
from productos.application.services import ProductoService
from productos.infrastructure.repositories import ProductoOrmRepository
from ventas.application.checkout_service import CheckoutService
from ventas.application.query_service import VentasQueryService
from ventas.application.venta_service import VentaService
from ventas.infrastructure.query_repository import VentasQueryRepository
from ventas.infrastructure.transaction_adapter import VentaTransactionAdapter


def get_producto_service() -> ProductoService:
    return ProductoService(ProductoOrmRepository())


def get_compra_service() -> CompraService:
    return CompraService(
        compra_repository=CompraOrmRepository(),
        producto_service=get_producto_service(),
    )


def get_carrito_service() -> CarritoService:
    return CarritoService(CarritoOrmRepository())


def get_carrito_query_service() -> CarritoQueryService:
    return CarritoQueryService(CarritoQueryRepository())


def get_pago_service() -> PagoService:
    return PagoService(PagoPersistenceAdapter())


def get_pago_query_service() -> PagoQueryService:
    return PagoQueryService(PagoQueryRepository())


def get_pago_state_service() -> PagoStateService:
    return PagoStateService(PagoPersistenceAdapter())


def get_envio_service() -> EnvioService:
    return EnvioService(EnvioOrmRepository())


def get_envio_query_service() -> EnvioQueryService:
    return EnvioQueryService(EnvioQueryRepository())


def get_orden_service() -> OrdenCompraService:
    return OrdenCompraService(OrdenPersistenceAdapter())


def get_orden_query_service() -> OrdenesQueryService:
    return OrdenesQueryService(OrdenesQueryRepository())


def get_atencion_service() -> AtencionClienteService:
    return AtencionClienteService(AtencionClienteOrmRepository())


def get_atencion_query_service() -> AtencionQueryService:
    return AtencionQueryService(AtencionQueryRepository())


def get_notificacion_service() -> NotificacionService:
    return NotificacionService(NotificacionOrmRepository())


def get_mensajeria_query_service() -> MensajeriaQueryService:
    return MensajeriaQueryService(MensajeriaQueryRepository())


def get_ventas_query_service() -> VentasQueryService:
    return VentasQueryService(VentasQueryRepository())


def get_checkout_service() -> CheckoutService:
    return CheckoutService(VentaTransactionAdapter())


def get_venta_service() -> VentaService:
    return VentaService(VentaTransactionAdapter())
