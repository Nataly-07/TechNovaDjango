"""
Validación de recepción de mercancía: stock, estado orden, auditoría.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from orden.infrastructure.models import DetalleOrden, OrdenCompra
from producto.models import Producto


class RecepcionOrdenError(ValueError):
    pass


@transaction.atomic
def validar_recepcion_mercancia(
    orden_id: int,
    *,
    usuario_id: int,
    cantidades_por_detalle_id: dict[int, int],
    observaciones: str,
) -> OrdenCompra:
    """
    Suma cantidades recibidas al stock, marca la orden como completada y registra auditoría.
    `cantidades_por_detalle_id`: id de DetalleOrden -> cantidad recibida (>= 0).
    """
    # Bloquear solo la fila de la orden (sin JOIN a FKs nulables: evita NotSupportedError en MySQL/PostgreSQL).
    orden = OrdenCompra.objects.select_for_update(of=("self",)).get(pk=orden_id)
    if orden.estado != OrdenCompra.Estado.PENDIENTE:
        raise RecepcionOrdenError(
            "Solo se puede validar recepción de órdenes aprobadas pendientes de ingreso al inventario."
        )

    detalles = list(
        DetalleOrden.objects.filter(orden_compra_id=orden.pk).select_related("producto")
    )
    if not detalles:
        raise RecepcionOrdenError("La orden no tiene líneas de producto.")

    obs = (observaciones or "").strip()

    for det in detalles:
        qty = cantidades_por_detalle_id.get(det.id, det.cantidad)
        try:
            qty_int = int(qty)
        except (TypeError, ValueError) as exc:
            raise RecepcionOrdenError("Cantidad recibida no válida.") from exc
        if qty_int < 0 or qty_int > 9999999:
            raise RecepcionOrdenError("La cantidad recibida debe estar entre 0 y un límite razonable.")

        producto = Producto.objects.select_for_update().get(pk=det.producto_id)
        producto.stock = int(producto.stock) + qty_int
        producto.save(update_fields=["stock", "actualizado_en"])

        det.cantidad_recibida = qty_int
        det.save(update_fields=["cantidad_recibida"])

    ahora = timezone.now()
    orden.estado = OrdenCompra.Estado.COMPLETADA
    orden.observaciones_recepcion = obs[:4000]
    orden.recepcion_validada_en = ahora
    orden.recepcion_validada_por_id = usuario_id
    orden.save(
        update_fields=[
            "estado",
            "observaciones_recepcion",
            "recepcion_validada_en",
            "recepcion_validada_por",
            "actualizado_en",
        ]
    )
    return orden
