from atencion_cliente.application.use_cases.atencion_cliente_usecases import (
    AtencionClienteService,
    AtencionQueryService,
)
from atencion_cliente.infrastructure.adapters.atencion_notificaciones_adapter import (
    AtencionNotificacionesDjango,
)
from atencion_cliente.infrastructure.repositories.atencion_cliente_repository_impl import (
    AtencionClienteOrmRepository,
)
from atencion_cliente.infrastructure.repositories.atencion_query_repository_impl import (
    AtencionQueryRepository,
)
from carrito.application.use_cases.carrito_usecases import (
    CarritoLineasService,
    CarritoQueryService,
    CarritoService,
)
from carrito.infrastructure.repositories.carrito_lineas_repository_impl import CarritoLineasRepository
from carrito.infrastructure.repositories.carrito_query_repository_impl import CarritoQueryRepository
from carrito.infrastructure.repositories.carrito_repository_impl import CarritoOrmRepository
from compra.application.use_cases.compra_usecases import CompraService
from compra.infrastructure.repositories.compra_repository_impl import CompraOrmRepository
from envio.application.use_cases.envio_usecases import EnvioQueryService, EnvioService
from envio.infrastructure.repositories.envio_query_repository_impl import EnvioQueryRepository
from envio.infrastructure.repositories.envio_repository_impl import EnvioOrmRepository
from mensajeria.application.use_cases.mensajeria_usecases import MensajeriaQueryService, NotificacionService
from mensajeria.infrastructure.repositories.mensajeria_query_repository_impl import MensajeriaQueryRepository
from mensajeria.infrastructure.repositories.notificacion_repository_impl import NotificacionOrmRepository
from orden.application.use_cases.orden_usecases import OrdenCompraService, OrdenQueryService
from orden.infrastructure.repositories.orden_compra_repository_impl import OrdenPersistenceAdapter
from orden.infrastructure.repositories.orden_query_repository_impl import OrdenQueryRepository
from pago.application.use_cases.pago_usecases import PagoQueryService, PagoService, PagoStateService
from pago.infrastructure.repositories.pago_query_repository_impl import PagoQueryRepository
from pago.infrastructure.repositories.pago_repository_impl import PagoPersistenceAdapter
from producto.application.use_cases.producto_usecases import ProductoService
from producto.infrastructure.repositories.producto_repository_impl import ProductoOrmRepository
from proveedor.application.use_cases.proveedor_usecases import ProveedorService
from proveedor.infrastructure.repositories.proveedor_repository_impl import ProveedorOrmRepository
from venta.application.use_cases.venta_usecases import CheckoutService, VentaService, VentaQueryService
from venta.infrastructure.repositories.venta_transaction_adapter_impl import VentaTransactionAdapter
from venta.infrastructure.repositories.venta_query_repository_impl import VentaQueryRepository


def get_producto_service() -> ProductoService:
    return ProductoService(ProductoOrmRepository())


def get_proveedor_service() -> ProveedorService:
    return ProveedorService(ProveedorOrmRepository())


def get_compra_service() -> CompraService:
    return CompraService(
        compra_repository=CompraOrmRepository(),
        producto_service=get_producto_service(),
    )


def get_carrito_service() -> CarritoService:
    return CarritoService(CarritoOrmRepository())


def get_carrito_query_service() -> CarritoQueryService:
    return CarritoQueryService(CarritoQueryRepository())


def get_carrito_lineas_service() -> CarritoLineasService:
    return CarritoLineasService(CarritoLineasRepository())


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


def get_orden_query_service() -> OrdenQueryService:
    return OrdenQueryService(OrdenQueryRepository())


def get_atencion_service() -> AtencionClienteService:
    return AtencionClienteService(
        AtencionClienteOrmRepository(),
        notificaciones=AtencionNotificacionesDjango(),
    )


def get_atencion_query_service() -> AtencionQueryService:
    return AtencionQueryService(AtencionQueryRepository())


def get_notificacion_service() -> NotificacionService:
    return NotificacionService(NotificacionOrmRepository())


def get_mensajeria_query_service() -> MensajeriaQueryService:
    return MensajeriaQueryService(MensajeriaQueryRepository())


def get_venta_query_service() -> VentaQueryService:
    return VentaQueryService(VentaQueryRepository())


def get_checkout_service() -> CheckoutService:
    return CheckoutService(VentaTransactionAdapter())


def get_venta_service() -> VentaService:
    return VentaService(VentaTransactionAdapter())
