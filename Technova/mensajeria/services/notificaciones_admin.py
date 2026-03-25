"""
Notificaciones dirigidas a cuentas administradoras (eventos del sistema).
"""
from __future__ import annotations

from decimal import Decimal

from mensajeria.models import Notificacion
from usuario.infrastructure.models.usuario_model import Usuario

# Umbral para avisar stock bajo (unidades)
STOCK_BAJO_UMBRAL = 5


def _ids_admins() -> list[int]:
    return list(
        Usuario.objects.filter(rol=Usuario.Rol.ADMIN, activo=True).values_list(
            "id", flat=True
        )
    )


def notificar_admins(
    *,
    titulo: str,
    mensaje: str,
    tipo: str,
    icono: str,
    data_adicional: dict | None = None,
) -> int:
    """Crea la misma notificación para cada administrador activo. Devuelve cantidad creada."""
    data = data_adicional if data_adicional is not None else {}
    t = (titulo or "")[:200]
    msg = mensaje or ""
    tp = (tipo or "general")[:50]
    ic = (icono or "bell")[:80]
    n = 0
    for uid in _ids_admins():
        Notificacion.objects.create(
            usuario_id=uid,
            titulo=t,
            mensaje=msg,
            tipo=tp,
            icono=ic,
            leida=False,
            data_adicional=data,
        )
        n += 1
    return n


def notificar_checkout_completado(
    *,
    venta_id: int,
    pago_id: int,
    envio_id: int,
    usuario_id: int,
    total: Decimal,
    metodo_pago: str,
    numero_factura: str,
    lineas: list[tuple[str, int]],
) -> None:
    cli = Usuario.objects.filter(pk=usuario_id).first()
    nombre = (
        f"{cli.nombres} {cli.apellidos}".strip() if cli else f"Usuario #{usuario_id}"
    )
    correo = cli.correo_electronico if cli else ""
    prod_txt = "\n".join(f"  • {nombre_p} × {cant}" for nombre_p, cant in lineas) or "  (sin detalle)"
    msg = (
        f"Nuevo pedido #{venta_id} — pago confirmado.\n\n"
        f"Cliente: {nombre}\n"
        f"Correo: {correo}\n"
        f"Total: ${total}\n"
        f"Método de pago: {metodo_pago}\n"
        f"Factura: {numero_factura}\n"
        f"Pago ID: {pago_id} · Envío ID: {envio_id}\n\n"
        f"Productos:\n{prod_txt}"
    )
    titulo = f"Nuevo pedido #{venta_id} · ${total} · {metodo_pago}"
    notificar_admins(
        titulo=titulo[:200],
        mensaje=msg,
        tipo="venta.pedido",
        icono="shopping-bag",
        data_adicional={
            "venta_id": venta_id,
            "pago_id": pago_id,
            "envio_id": envio_id,
            "usuario_id": usuario_id,
        },
    )


def notificar_pedido_anulado(
    *,
    venta_id: int,
    cliente_label: str,
    monto: Decimal | None = None,
) -> None:
    extra = f" · Total devuelto/ref.: ${monto}" if monto is not None else ""
    msg = (
        f"El pedido #{venta_id} fue anulado.{extra}\n"
        f"Cliente: {cliente_label}\n"
        f"Se revirtió stock y se marcó reembolso de pago según corresponda."
    )
    notificar_admins(
        titulo=f"Pedido cancelado · #{venta_id}",
        mensaje=msg,
        tipo="venta.anulada",
        icono="x-circle",
        data_adicional={"venta_id": venta_id},
    )


def notificar_pago_rechazado(
    *,
    pago_id: int,
    monto: Decimal,
    numero_factura: str,
) -> None:
    msg = (
        f"Pago #{pago_id} rechazado.\n"
        f"Monto: ${monto}\n"
        f"Factura: {numero_factura}"
    )
    notificar_admins(
        titulo=f"Pago rechazado · ${monto}",
        mensaje=msg,
        tipo="pago.rechazado",
        icono="credit-card",
        data_adicional={"pago_id": pago_id},
    )


def notificar_envio_cambio_estado(
    *,
    envio_id: int,
    venta_id: int,
    estado_anterior: str,
    estado_nuevo: str,
    guia: str,
) -> None:
    msg = (
        f"Envío #{envio_id} (pedido #{venta_id})\n"
        f"Guía: {guia}\n"
        f"Estado: {estado_anterior} → {estado_nuevo}"
    )
    if estado_nuevo in ("en_ruta", "entregado"):
        titulo = (
            "Pedido en ruta"
            if estado_nuevo == "en_ruta"
            else "Pedido entregado"
        )
        titulo = f"{titulo} · #{venta_id}"
    else:
        titulo = f"Actualización de envío · pedido #{venta_id}"
    notificar_admins(
        titulo=titulo[:200],
        mensaje=msg,
        tipo="envio.estado",
        icono="package",
        data_adicional={"envio_id": envio_id, "venta_id": venta_id},
    )


def notificar_usuario_nuevo(usuario: Usuario) -> None:
    msg = (
        f"Nuevo usuario en el sistema.\n"
        f"Nombre: {usuario.nombres} {usuario.apellidos}\n"
        f"Correo: {usuario.correo_electronico}\n"
        f"Rol: {usuario.get_rol_display()}"
    )
    notificar_admins(
        titulo=f"Nuevo usuario · {usuario.correo_electronico}",
        mensaje=msg,
        tipo="usuario.nuevo",
        icono="user-plus",
        data_adicional={"usuario_id": usuario.id},
    )


def notificar_producto_nuevo(producto_id: int, nombre: str, stock: int) -> None:
    if stock == 0:
        extra = " (sin inventario — considera reabastecer)"
    elif 0 < stock <= STOCK_BAJO_UMBRAL:
        extra = f" (stock bajo: {stock} unidades)"
    else:
        extra = ""
    msg = f"Producto registrado: {nombre}\nID: {producto_id}\nStock inicial: {stock}{extra}"
    notificar_admins(
        titulo=f"Producto nuevo · {nombre[:80]}",
        mensaje=msg,
        tipo="inventario.producto_nuevo",
        icono="cube",
        data_adicional={"producto_id": producto_id},
    )


def notificar_stock_bajo(producto_id: int, nombre: str, stock: int) -> None:
    msg = (
        f"Stock bajo ({STOCK_BAJO_UMBRAL} o menos unidades).\n"
        f"Producto: {nombre}\n"
        f"ID: {producto_id}\n"
        f"Stock actual: {stock}"
    )
    notificar_admins(
        titulo=f"Stock bajo · {nombre[:60]}",
        mensaje=msg,
        tipo="inventario.stock_bajo",
        icono="error",
        data_adicional={"producto_id": producto_id, "stock": stock},
    )


def notificar_producto_agotado(producto_id: int, nombre: str) -> None:
    msg = f"Sin stock: {nombre}\nID producto: {producto_id}"
    notificar_admins(
        titulo=f"Producto agotado · {nombre[:60]}",
        mensaje=msg,
        tipo="inventario.agotado",
        icono="error-circle",
        data_adicional={"producto_id": producto_id},
    )
