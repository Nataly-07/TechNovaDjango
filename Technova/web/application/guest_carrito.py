"""
Carrito de invitado en sesión Django (sin `usuario_id` en BD).
Las líneas usan `detalle_id` sintético negativo: `-producto_id`.
Al iniciar sesión se fusionan con `CarritoLineasService`.
"""

from __future__ import annotations

from decimal import Decimal

from django.http import HttpRequest

from common.container import get_carrito_lineas_service
from producto.models import Producto

SESSION_GUEST_CART = "technova_guest_cart_v1"


def _guest_lines(request: HttpRequest) -> list[dict]:
    raw = request.session.get(SESSION_GUEST_CART)
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            pid = int(row.get("producto_id"))
            qty = int(row.get("cantidad", 1))
        except (TypeError, ValueError):
            continue
        if pid < 1 or qty < 1:
            continue
        out.append({"producto_id": pid, "cantidad": qty})
    return out


def _set_guest_lines(request: HttpRequest, lines: list[dict]) -> None:
    request.session[SESSION_GUEST_CART] = lines
    request.session.modified = True


def guest_cart_clear(request: HttpRequest) -> None:
    if SESSION_GUEST_CART in request.session:
        del request.session[SESSION_GUEST_CART]
        request.session.modified = True


def guest_cart_has_items(request: HttpRequest) -> bool:
    return bool(_guest_lines(request))


def guest_cart_add(request: HttpRequest, producto_id: int, cantidad: int = 1) -> None:
    if cantidad < 1:
        cantidad = 1
    producto = Producto.objects.filter(id=producto_id).first()
    if producto is None:
        raise ValueError(f"Producto no encontrado: {producto_id}")
    if not producto.activo:
        raise ValueError("El producto no esta disponible.")
    if producto.stock is None or producto.stock <= 0:
        raise ValueError("El producto esta agotado y no se puede agregar al carrito")

    lines = _guest_lines(request)
    merged = False
    for row in lines:
        if row["producto_id"] == producto_id:
            nueva = row["cantidad"] + cantidad
            if producto.stock < nueva:
                raise ValueError("No hay suficiente stock disponible")
            row["cantidad"] = nueva
            merged = True
            break
    if not merged:
        if producto.stock < cantidad:
            raise ValueError("No hay suficiente stock disponible")
        lines.append({"producto_id": producto_id, "cantidad": cantidad})
    _set_guest_lines(request, lines)


def guest_cart_line_items(request: HttpRequest) -> list[dict]:
    """Misma forma que `CarritoLineasRepository._lineas_a_dto` para plantillas y totales."""
    raw_lines = _guest_lines(request)
    rows: list[dict] = []
    kept: list[dict] = []
    for row in raw_lines:
        p = Producto.objects.filter(id=row["producto_id"]).first()
        if p is None or not p.activo:
            continue
        qty = int(row["cantidad"])
        if qty < 1:
            qty = 1
        if p.stock is not None and qty > p.stock:
            qty = int(p.stock)
        if qty < 1:
            continue
        kept.append({"producto_id": p.id, "cantidad": qty})
        precio = p.precio_venta
        precio_dec = Decimal("0") if precio is None else precio
        subtotal = precio_dec * qty
        rows.append(
            {
                "detalle_id": -int(p.id),
                "producto_id": p.id,
                "nombre_producto": p.nombre,
                "imagen": p.imagen_url or "",
                "cantidad": qty,
                "stock": p.stock or 0,
                "precio_unitario": str(precio_dec),
                "subtotal_linea": str(subtotal),
            }
        )
    if len(kept) != len(raw_lines):
        _set_guest_lines(request, kept)
    return rows


def guest_cart_preview(request: HttpRequest, limit: int = 8) -> list[dict]:
    out: list[dict] = []
    for it in guest_cart_line_items(request)[:limit]:
        out.append(
            {
                "detalle_id": it.get("detalle_id"),
                "producto_id": it.get("producto_id"),
                "nombre_producto": it.get("nombre_producto", ""),
                "imagen": it.get("imagen") or "",
                "cantidad": int(it.get("cantidad", 1)),
                "stock": int(it.get("stock", 0) or 0),
                "precio_unitario": str(it.get("precio_unitario", "0")),
            }
        )
    return out


def guest_cart_update(request: HttpRequest, detalle_id: int, cantidad: int) -> None:
    if detalle_id >= 0:
        raise ValueError("Linea de invitado no valida.")
    producto_id = -detalle_id
    if cantidad < 1:
        cantidad = 1
    producto = Producto.objects.filter(id=producto_id).first()
    if producto is None or not producto.activo:
        raise ValueError("El producto no esta disponible.")
    if producto.stock is not None and cantidad > producto.stock:
        raise ValueError("No hay suficiente stock disponible")

    lines = _guest_lines(request)
    found = False
    new_lines: list[dict] = []
    for row in lines:
        if row["producto_id"] == producto_id:
            new_lines.append({"producto_id": producto_id, "cantidad": cantidad})
            found = True
        else:
            new_lines.append(dict(row))
    if not found:
        raise ValueError("Linea no encontrada en el carrito de invitado.")
    _set_guest_lines(request, new_lines)


def guest_cart_remove(request: HttpRequest, detalle_id: int) -> None:
    if detalle_id >= 0:
        raise ValueError("Linea de invitado no valida.")
    producto_id = -detalle_id
    lines = [r for r in _guest_lines(request) if r["producto_id"] != producto_id]
    _set_guest_lines(request, lines)


def merge_guest_cart_into_user(request: HttpRequest, usuario_id: int) -> None:
    lines = _guest_lines(request)
    if not lines:
        return
    svc = get_carrito_lineas_service()
    for row in lines:
        try:
            svc.agregar_producto(usuario_id, int(row["producto_id"]), int(row["cantidad"]))
        except ValueError:
            continue
    guest_cart_clear(request)
