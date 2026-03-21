from dataclasses import dataclass

from django.db import transaction

from envios.models import Envio
from pagos.models import Pago
from productos.models import Producto
from ventas.models import DetalleVenta, Venta


@dataclass(frozen=True)
class AnulacionVentaResultado:
    venta_id: int
    pagos_reembolsados: int
    items_revertidos: int


class VentaService:
    @transaction.atomic
    def anular_venta(self, venta_id: int) -> AnulacionVentaResultado:
        venta = Venta.objects.select_for_update().filter(id=venta_id).first()
        if venta is None:
            raise ValueError("La venta no existe.")
        if venta.estado == Venta.Estado.ANULADA:
            raise ValueError("La venta ya se encuentra anulada.")

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

        return AnulacionVentaResultado(
            venta_id=venta.id,
            pagos_reembolsados=pagos_reembolsados,
            items_revertidos=items_revertidos,
        )
