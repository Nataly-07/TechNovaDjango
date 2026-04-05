"""Filtros de plantilla para moneda COP (miles con punto, decimales con coma)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django import template

register = template.Library()


def _to_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return None


@register.filter(name="format_cop")
def format_cop(value):
    """
    Formato visual tipo $9.600.000,00 (sin depender de locale del SO).
    """
    d = _to_decimal(value)
    if d is None:
        return "—"
    negative = d < 0
    d = abs(d)
    s = format(d, "f")
    if "." in s:
        whole, frac = s.split(".", 1)
    else:
        whole, frac = s, "00"
    frac = (frac + "00")[:2]
    whole = whole.lstrip("0") or "0"
    parts: list[str] = []
    while whole:
        parts.insert(0, whole[-3:])
        whole = whole[:-3]
    whole_fmt = ".".join(parts)
    sign = "-" if negative else ""
    return f"{sign}${whole_fmt},{frac}"
