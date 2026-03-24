from datetime import date

from django.conf import settings

from pago.models import MedioPago, Pago
from usuario.infrastructure.models.usuario_model import Usuario
from venta.models import Venta

from web.domain.constants import FACTURA_VENTA_PATTERN


def parse_date_param(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def extraer_venta_id_factura(numero_factura: str | None) -> int | None:
    if not numero_factura:
        return None
    m = FACTURA_VENTA_PATTERN.match(numero_factura.strip())
    if m:
        return int(m.group(1))
    s = numero_factura.strip()
    if s.isdigit():
        vid = int(s)
        if Venta.objects.filter(pk=vid).exists():
            return vid
    return None


def venta_cliente_desde_pago(pago: Pago) -> tuple[Venta | None, Usuario | None]:
    medios = list(pago.medios_pago.all())
    if medios:
        venta = medios[0].detalle_venta.venta
        return venta, venta.usuario
    vid = extraer_venta_id_factura(pago.numero_factura)
    if vid:
        venta = Venta.objects.select_related("usuario").filter(pk=vid).first()
        if venta:
            return venta, venta.usuario
    return None, None


def badge_clase_estado_pago(estado: str) -> str:
    e = (estado or "").lower()
    if e == Pago.EstadoPago.APROBADO:
        return "confirmado"
    if e == Pago.EstadoPago.PENDIENTE:
        return "pendiente"
    if e in (Pago.EstadoPago.RECHAZADO, Pago.EstadoPago.REEMBOLSADO):
        return "cancelado"
    return "pendiente"


def fecha_larga_es(d: date | None) -> str:
    if d is None:
        return "—"
    meses = (
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    )
    return f"{d.day} de {meses[d.month - 1].capitalize()} de {d.year}"


def etiqueta_medio_pago_mostrar(medio: MedioPago | None) -> str:
    """Texto mostrado en admin (corrige etiqueta PSE cuando el pago fue PayPal en checkout web)."""
    if medio is None:
        return ""
    if medio.metodo_pago == MedioPago.Metodo.PSE.value and getattr(
        settings, "TECHNOVA_ADMIN_PSE_LEGACY_COMO_PAYPAL", True
    ):
        return "PayPal"
    return medio.get_metodo_pago_display()


def lista_metodos_pago_display(pago: Pago) -> list[str]:
    """Etiquetas legibles únicas (por código de método) según medios asociados al pago."""
    seen: set[str] = set()
    out: list[str] = []
    for m in pago.medios_pago.all():
        if m.metodo_pago not in seen:
            seen.add(m.metodo_pago)
            out.append(etiqueta_medio_pago_mostrar(m))
    return out


def filtrar_queryset_pagos_por_estado_get(qs, estado_raw: str | None):
    if not estado_raw:
        return qs
    e = estado_raw.strip().upper()
    if e in ("CONFIRMADO", "APROBADO"):
        return qs.filter(estado_pago=Pago.EstadoPago.APROBADO)
    if e == "PENDIENTE":
        return qs.filter(estado_pago=Pago.EstadoPago.PENDIENTE)
    if e in ("CANCELADO", "RECHAZADO", "REEMBOLSADO"):
        return qs.filter(
            estado_pago__in=[Pago.EstadoPago.RECHAZADO, Pago.EstadoPago.REEMBOLSADO]
        )
    return qs
