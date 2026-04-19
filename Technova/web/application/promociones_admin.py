"""Validación y persistencia de promociones de producto (admin + correos)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from producto.models import Producto
from web.templatetags.currency_extras import format_cop

MSG_FECHA_OBLIGATORIA = "Por favor, selecciona una fecha de vencimiento para la oferta."


def producto_fila_precio_tabla(producto: Producto) -> dict:
    """Payload para actualizar la columna de precios en la tabla de inventario."""
    producto.refresh_from_db()
    return {
        "id": producto.id,
        "promocion_activa": bool(producto.promocion_activa),
        "precio_base_fmt": format_cop(producto.precio_base),
        "precio_promocion_fmt": format_cop(producto.precio_promocion)
        if producto.precio_promocion is not None
        else None,
    }


def validar_parse_fecha_fin_promocion(fecha_fin_raw: str | None) -> tuple[datetime | None, str | None]:
    """
    Retorna (datetime con zona, None) si es válida y futura.
    Retorna (None, mensaje_error) si falla.
    """
    raw = (fecha_fin_raw or "").strip()
    if not raw:
        return None, MSG_FECHA_OBLIGATORIA
    dt_fin = parse_datetime(raw)
    if dt_fin is None:
        return None, "Fecha fin de promoción inválida."
    if timezone.is_naive(dt_fin):
        dt_fin = timezone.make_aware(dt_fin, timezone.get_current_timezone())
    if dt_fin <= timezone.now():
        return None, "La fecha fin de promoción debe ser futura."
    return dt_fin, None


def aplicar_promocion_en_producto(
    producto: Producto, precio_promocion: Decimal, dt_fin: datetime
) -> None:
    producto.precio_promocion = precio_promocion
    producto.fecha_fin_promocion = dt_fin
    producto.save(update_fields=["precio_promocion", "fecha_fin_promocion", "actualizado_en"])


def terminar_promocion_en_producto(producto: Producto) -> None:
    producto.precio_promocion = None
    producto.fecha_fin_promocion = None
    producto.save(update_fields=["precio_promocion", "fecha_fin_promocion", "actualizado_en"])


def decimal_desde_str(val) -> Decimal | None:
    if val is None:
        return None
    s = str(val).strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError, TypeError):
        return None


def validar_precio_promocion_contra_base(
    precio_promo: Decimal, producto: Producto
) -> str | None:
    """None si OK; mensaje en español si no."""
    base = producto.precio_base
    if base is None:
        return "El producto no tiene precio base definido."
    try:
        base_d = Decimal(str(base))
    except (InvalidOperation, TypeError, ValueError):
        return "El precio base del producto no es válido."
    if precio_promo <= 0:
        return "El precio de promoción debe ser mayor a 0."
    if precio_promo >= base_d:
        return "El precio de promoción debe ser menor que el precio de venta regular."
    return None


def cerrar_promociones_productos_vencidas() -> int:
    """
    Quita precio_promocion y fecha_fin en productos cuya fecha de fin ya pasó.
    Devuelve el número de filas actualizadas.
    """
    now = timezone.now()
    return Producto.objects.filter(
        fecha_fin_promocion__isnull=False,
        fecha_fin_promocion__lt=now,
    ).update(
        precio_promocion=None,
        fecha_fin_promocion=None,
        actualizado_en=now,
    )
