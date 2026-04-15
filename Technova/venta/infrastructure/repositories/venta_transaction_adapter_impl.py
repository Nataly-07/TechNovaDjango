from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from carrito.models import Carrito
from envio.models import Envio
from correos.compra_notificacion_service import enviar_correo_compra_confirmada_cliente
from mensajeria.services.notificaciones_admin import (
    notificar_checkout_completado,
    notificar_pedido_anulado,
    notificar_pago_registrado,
    notificar_stock_disminuido,
)
from pago.models import MedioPago, Pago
from producto.models import Producto
from usuario.models import Usuario
from venta.domain.repositories import CheckoutPort, VentaAnulacionPort
from venta.domain.results import AnulacionVentaResultado, CheckoutResultado
from venta.domain.value_objects import Dinero, NumeroFactura
from venta.models import DetalleVenta, Venta


class VentaTransactionAdapter(CheckoutPort, VentaAnulacionPort):
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
        usuario_id: int,
        carrito_id: int,
        metodo_pago: str,
        numero_factura: str,
        fecha_factura: date,
        transportadora_id: int,
        numero_guia: str,
        costo_envio: Decimal = Decimal("0"),
    ) -> CheckoutResultado:
        NumeroFactura.crear(numero_factura)

        previo = self._resultado_desde_numero_factura(numero_factura=numero_factura)
        if previo is not None:
            return previo

        carrito = (
            Carrito.objects.select_for_update()
            .filter(id=carrito_id, usuario_id=usuario_id, estado=Carrito.Estado.ACTIVO)
            .first()
        )
        if carrito is None:
            raise ValueError("No existe un carrito activo para el usuario.")

        detalles_carrito = list(carrito.detalles.select_for_update().all())
        if not detalles_carrito:
            raise ValueError("El carrito no tiene productos.")

        usuario_checkout = Usuario.objects.filter(pk=usuario_id).first()
        if usuario_checkout is None:
            raise ValueError("Usuario no encontrado.")
        if usuario_checkout.rol == Usuario.Rol.CLIENTE and not usuario_checkout.correo_verificado:
            raise ValueError(
                "Debes confirmar tu correo electrónico antes de completar la compra."
            )

        total_productos = Decimal("0")
        venta = Venta.objects.create(
            usuario_id=usuario_id,
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
            stock_anterior = int(producto.stock)

            precio_unitario = (
                producto.precio_venta
                if producto.precio_venta is not None
                else producto.costo_unitario
            )
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
            stock_actual = int(producto.stock)

            def _notificar_stock(pid=producto.id, nombre=producto.nombre, prev=stock_anterior, cur=stock_actual) -> None:
                notificar_stock_disminuido(
                    producto_id=pid,
                    nombre=nombre,
                    stock_anterior=prev,
                    stock_actual=cur,
                    motivo="venta",
                )

            transaction.on_commit(_notificar_stock)

        total_final = total_productos + costo_envio
        Dinero.crear(total_final)
        venta.total = total_final
        venta.save(update_fields=["total", "actualizado_en"])

        pago = Pago.objects.create(
            fecha_pago=timezone.localdate(),
            numero_factura=numero_factura,
            fecha_factura=fecha_factura,
            monto=total_final,
            estado_pago=Pago.EstadoPago.APROBADO,
        )

        def _notificar_pago() -> None:
            notificar_pago_registrado(
                pago_id=pago.id,
                monto=pago.monto,
                numero_factura=pago.numero_factura,
            )

        transaction.on_commit(_notificar_pago)

        for detalle in detalles_venta:
            MedioPago.objects.create(
                pago=pago,
                detalle_venta=detalle,
                usuario_id=usuario_id,
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

        lineas = [(d.producto.nombre, d.cantidad) for d in detalles_venta]

        def _notificar_pedido() -> None:
            notificar_checkout_completado(
                venta_id=venta.id,
                pago_id=pago.id,
                envio_id=envio.id,
                usuario_id=usuario_id,
                total=total_final,
                metodo_pago=metodo_pago,
                numero_factura=numero_factura,
                lineas=lineas,
            )

        transaction.on_commit(_notificar_pedido)

        def _correo_cliente() -> None:
            enviar_correo_compra_confirmada_cliente(
                venta_id=venta.id,
                pago_id=pago.id,
                canal="online",
            )

        transaction.on_commit(_correo_cliente)

        return CheckoutResultado(
            venta_id=venta.id,
            pago_id=pago.id,
            envio_id=envio.id,
            total=total_final,
            idempotente=False,
        )

    @transaction.atomic
    def anular_venta(self, venta_id: int) -> AnulacionVentaResultado:
        venta = Venta.objects.select_for_update().filter(id=venta_id).first()
        if venta is None:
            raise ValueError("La venta no existe.")
        if venta.estado == Venta.Estado.ANULADA:
            raise ValueError("La venta ya se encuentra anulada.")

        cli = Usuario.objects.filter(pk=venta.usuario_id).first()
        cliente_label = (
            f"{cli.nombres} {cli.apellidos}".strip() if cli else f"Usuario #{venta.usuario_id}"
        )
        monto_venta = venta.total

        detalles = (
            DetalleVenta.objects.select_for_update()
            .select_related("producto")
            .filter(venta_id=venta.id)
        )

        items_revertidos = 0
        for detalle in detalles:
            producto = Producto.objects.select_for_update().filter(id=detalle.producto_id).first()
            if producto is None:
                continue
            producto.stock += detalle.cantidad
            producto.save(update_fields=["stock", "actualizado_en"])
            items_revertidos += 1

        pago_ids = list(
            Pago.objects.filter(medios_pago__detalle_venta__venta_id=venta.id)
            .values_list("id", flat=True)
            .distinct()
        )
        pagos = Pago.objects.select_for_update().filter(id__in=pago_ids)
        pagos_reembolsados = 0
        for pago in pagos:
            if pago.estado_pago != Pago.EstadoPago.REEMBOLSADO:
                pago.estado_pago = Pago.EstadoPago.REEMBOLSADO
                pago.save(update_fields=["estado_pago", "actualizado_en"])
                pagos_reembolsados += 1

        Envio.objects.filter(venta_id=venta.id, activo=True).update(
            estado=Envio.Estado.DEVUELTO,
            activo=False,
        )

        venta.estado = Venta.Estado.ANULADA
        venta.save(update_fields=["estado", "actualizado_en"])

        def _notificar_anulacion() -> None:
            notificar_pedido_anulado(
                venta_id=venta.id,
                cliente_label=cliente_label,
                monto=monto_venta,
            )

        transaction.on_commit(_notificar_anulacion)

        return AnulacionVentaResultado(
            venta_id=venta.id,
            pagos_reembolsados=pagos_reembolsados,
            items_revertidos=items_revertidos,
        )
