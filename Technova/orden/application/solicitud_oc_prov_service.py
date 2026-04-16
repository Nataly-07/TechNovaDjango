"""
Lógica de solicitudes de reabastecimiento (empleado → admin → OrdenCompra).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from mensajeria.models import Notificacion
from orden.infrastructure.models import DetalleOrden, OrdenCompra, SolicitudOrdenCompraProv
from producto.models import Producto
from usuario.infrastructure.models.usuario_model import Usuario


def _ids_admins() -> list[int]:
    return list(
        Usuario.objects.filter(rol=Usuario.Rol.ADMIN, activo=True).values_list("id", flat=True)
    )


def aplicar_snapshots_desde_producto(
    solicitud: SolicitudOrdenCompraProv,
    *,
    sobrescribir_costo_desde_catalogo: bool = True,
) -> None:
    """Copia proveedor, marca y color desde el producto. El costo solo se toma del catálogo si se indica."""
    p = solicitud.producto
    solicitud.proveedor_id = p.proveedor_id
    solicitud.marca_snapshot = p.marca or ""
    solicitud.color_snapshot = p.color or ""
    if sobrescribir_costo_desde_catalogo:
        solicitud.costo_unitario_snapshot = p.costo_unitario or Decimal("0")


def actualizar_producto_costo_y_precio_venta_por_margen(
    producto: Producto,
    nuevo_costo: Decimal,
) -> dict:
    """
    Persiste el nuevo costo en el catálogo. Si hay precio de venta y costo previo > 0,
    mantiene la misma relación precio/costo (margen implícito sobre el costo anterior).
    """
    nuevo_costo = nuevo_costo.quantize(Decimal("0.01"))
    old_costo = producto.costo_unitario or Decimal("0")
    old_pv = producto.precio_venta
    producto.costo_unitario = nuevo_costo
    nuevo_pv = None
    if old_pv is not None and old_costo > 0:
        ratio = old_pv / old_costo
        nuevo_pv = (nuevo_costo * ratio).quantize(Decimal("0.01"))
        producto.precio_venta = nuevo_pv
    producto.save(update_fields=["costo_unitario", "precio_venta", "actualizado_en"])
    return {
        "precio_venta_actualizado": nuevo_pv is not None,
        "nuevo_precio_venta": nuevo_pv,
    }


def notificar_admins_solicitud_pendiente(solicitud: SolicitudOrdenCompraProv) -> int:
    """Una notificación por cada admin: nueva solicitud pendiente."""
    n = 0
    emp = solicitud.empleado
    label = f"{emp.nombres} {emp.apellidos}".strip() or emp.correo_electronico
    titulo = f"Solicitud OC Prov #{solicitud.id} pendiente"
    mensaje = (
        f"{label} envió una solicitud de reabastecimiento.\n"
        f"Producto: {solicitud.producto.nombre} (cantidad: {solicitud.cantidad})."
    )
    for uid in _ids_admins():
        Notificacion.objects.create(
            usuario_id=uid,
            titulo=titulo[:200],
            mensaje=mensaje,
            tipo="orden.solicitud_oc_prov",
            icono="clipboard-list",
            leida=False,
            data_adicional={
                "solicitud_id": solicitud.id,
                "producto_id": solicitud.producto_id,
            },
        )
        n += 1
    return n


def notificar_empleado_solicitud_resuelta(
    solicitud: SolicitudOrdenCompraProv,
    *,
    aprobada: bool,
) -> None:
    if aprobada:
        titulo = f"Solicitud #{solicitud.id} aprobada"
        oc_id = solicitud.orden_compra_id
        mensaje = (
            "Tu solicitud de orden de compra fue aprobada."
            + (f" Orden de compra oficial #{oc_id}." if oc_id else "")
        )
        icono = "check-circle"
    else:
        titulo = f"Solicitud #{solicitud.id} rechazada"
        mensaje = (solicitud.motivo_rechazo or "Tu solicitud fue rechazada.").strip()
        icono = "x-circle"
    Notificacion.objects.create(
        usuario_id=solicitud.empleado_id,
        titulo=titulo[:200],
        mensaje=mensaje[:2000],
        tipo="orden.solicitud_oc_prov.resuelta",
        icono=icono,
        leida=False,
        data_adicional={
            "solicitud_id": solicitud.id,
            "aprobada": aprobada,
            "orden_compra_id": solicitud.orden_compra_id,
        },
    )


def enviar_solicitud_al_admin(solicitud: SolicitudOrdenCompraProv) -> SolicitudOrdenCompraProv:
    if solicitud.estado != SolicitudOrdenCompraProv.Estado.BORRADOR:
        raise ValueError("Solo se pueden enviar solicitudes que aún están en edición.")
    solicitud.estado = SolicitudOrdenCompraProv.Estado.PENDIENTE
    solicitud.enviada_en = timezone.now()
    solicitud.save(update_fields=["estado", "enviada_en", "actualizado_en"])
    notificar_admins_solicitud_pendiente(solicitud)
    return solicitud


@transaction.atomic
def aprobar_y_generar_orden(
    solicitud_id: int,
    *,
    proveedor_id: int,
    cantidad: int,
    precio_unitario: Decimal,
) -> tuple[SolicitudOrdenCompraProv, OrdenCompra, dict]:
    solicitud = (
        SolicitudOrdenCompraProv.objects.select_for_update()
        .select_related("producto", "empleado")
        .get(pk=solicitud_id)
    )
    if solicitud.estado != SolicitudOrdenCompraProv.Estado.PENDIENTE:
        raise ValueError("La solicitud no está pendiente de aprobación.")

    producto = Producto.objects.select_for_update().get(pk=solicitud.producto_id)
    precio = precio_unitario.quantize(Decimal("0.01"))
    if precio < 0:
        raise ValueError("El costo unitario no puede ser negativo.")
    qty = int(cantidad)
    if qty < 1:
        raise ValueError("La cantidad debe ser al menos 1.")
    subtotal = (Decimal(qty) * precio).quantize(Decimal("0.01"))

    orden = OrdenCompra.objects.create(
        proveedor_id=proveedor_id,
        fecha=date.today(),
        total=subtotal,
        estado=OrdenCompra.Estado.PENDIENTE,
    )
    DetalleOrden.objects.create(
        orden_compra=orden,
        producto=producto,
        cantidad=qty,
        precio_unitario=precio,
        subtotal=subtotal,
    )

    catalogo_info = actualizar_producto_costo_y_precio_venta_por_margen(producto, precio)

    solicitud.estado = SolicitudOrdenCompraProv.Estado.APROBADA
    solicitud.proveedor_id = proveedor_id
    solicitud.cantidad_aprobada = qty
    solicitud.costo_unitario_snapshot = precio
    solicitud.orden_compra = orden
    solicitud.resuelta_en = timezone.now()
    solicitud.save(
        update_fields=[
            "estado",
            "proveedor",
            "cantidad_aprobada",
            "costo_unitario_snapshot",
            "orden_compra",
            "resuelta_en",
            "actualizado_en",
        ]
    )

    notificar_empleado_solicitud_resuelta(solicitud, aprobada=True)
    return solicitud, orden, catalogo_info


def rechazar_solicitud(
    solicitud_id: int,
    *,
    motivo: str,
) -> SolicitudOrdenCompraProv:
    solicitud = SolicitudOrdenCompraProv.objects.select_related("empleado").get(pk=solicitud_id)
    if solicitud.estado != SolicitudOrdenCompraProv.Estado.PENDIENTE:
        raise ValueError("La solicitud no está pendiente.")
    solicitud.estado = SolicitudOrdenCompraProv.Estado.RECHAZADA
    solicitud.motivo_rechazo = (motivo or "").strip() or "Sin motivo indicado."
    solicitud.resuelta_en = timezone.now()
    solicitud.save(update_fields=["estado", "motivo_rechazo", "resuelta_en", "actualizado_en"])
    notificar_empleado_solicitud_resuelta(solicitud, aprobada=False)
    return solicitud
