from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from carrito.models import Carrito
from envios.models import Envio
from pagos.models import MedioPago, Pago
from productos.models import Producto
from usuarios.models import Usuario
from ventas.models import DetalleVenta, Venta


@dataclass(frozen=True)
class CheckoutResultado:
    venta_id: int
    pago_id: int
    envio_id: int
    total: Decimal
    idempotente: bool = False


class CheckoutService:
    def _resultado_desde_numero_factura(self, numero_factura: str) -> CheckoutResultado | None:
        pago = (
            Pago.objects.filter(numero_factura=numero_factura)
            .prefetch_related("medios_pago__detalle_venta__venta__envios")
            .first()
        )
        if pago is None:
            return None

        medio = pago.medios_pago.first()
        if medio is None:
            return None

        venta = medio.detalle_venta.venta
        envio = venta.envios.order_by("-id").first()
        if envio is None:
            return None

        return CheckoutResultado(
            venta_id=venta.id,
            pago_id=pago.id,
            envio_id=envio.id,
            total=venta.total,
            idempotente=True,
        )

    @transaction.atomic
    def ejecutar_checkout(
        self,
        *,
        usuario: Usuario,
        carrito_id: int,
        metodo_pago: str,
        numero_factura: str,
        fecha_factura: date,
        transportadora_id: int,
        numero_guia: str,
        costo_envio: Decimal = Decimal("0"),
    ) -> CheckoutResultado:
        if not numero_factura.strip():
            raise ValueError("El numero de factura es obligatorio.")

        previo = self._resultado_desde_numero_factura(numero_factura=numero_factura)
        if previo is not None:
            return previo

        carrito = (
            Carrito.objects.select_for_update()
            .filter(id=carrito_id, usuario_id=usuario.id, estado=Carrito.Estado.ACTIVO)
            .first()
        )
        if carrito is None:
            raise ValueError("No existe un carrito activo para el usuario.")

        detalles_carrito = list(carrito.detalles.select_for_update().all())
        if not detalles_carrito:
            raise ValueError("El carrito no tiene productos.")

        total_productos = Decimal("0")
        venta = Venta.objects.create(
            usuario_id=usuario.id,
            fecha_venta=timezone.localdate(),
            estado=Venta.Estado.FACTURADA,
            total=Decimal("0"),
        )

        detalles_venta = []
        for item in detalles_carrito:
            producto = Producto.objects.select_for_update().filter(id=item.producto_id, activo=True).first()
            if producto is None:
                raise ValueError(f"Producto no disponible: {item.producto_id}")
            if producto.stock < item.cantidad:
                raise ValueError(f"Stock insuficiente para {producto.nombre}.")

            precio_unitario = producto.costo_unitario
            subtotal = precio_unitario * item.cantidad
            total_productos += subtotal

            detalle = DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=item.cantidad,
                precio_unitario=precio_unitario,
            )
            detalles_venta.append(detalle)

            producto.stock -= item.cantidad
            producto.save(update_fields=["stock", "actualizado_en"])

        total_final = total_productos + costo_envio
        venta.total = total_final
        venta.save(update_fields=["total", "actualizado_en"])

        pago = Pago.objects.create(
            fecha_pago=timezone.localdate(),
            numero_factura=numero_factura,
            fecha_factura=fecha_factura,
            monto=total_final,
            estado_pago=Pago.EstadoPago.APROBADO,
        )

        for detalle in detalles_venta:
            MedioPago.objects.create(
                pago=pago,
                detalle_venta=detalle,
                usuario=usuario,
                metodo_pago=metodo_pago,
                fecha_compra=timezone.now(),
                tiempo_entrega=None,
                activo=True,
            )

        envio = Envio.objects.create(
            venta=venta,
            transportadora_id=transportadora_id,
            fecha_envio=timezone.now(),
            numero_guia=numero_guia,
            costo_envio=costo_envio,
            estado=Envio.Estado.PREPARANDO,
            activo=True,
        )

        carrito.estado = Carrito.Estado.CERRADO
        carrito.save(update_fields=["estado"])
        carrito.detalles.all().delete()

        return CheckoutResultado(
            venta_id=venta.id,
            pago_id=pago.id,
            envio_id=envio.id,
            total=total_final,
            idempotente=False,
        )
