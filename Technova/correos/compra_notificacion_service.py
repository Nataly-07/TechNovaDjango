"""
Envío de correo al cliente cuando se confirma una compra (tienda online o punto físico).
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from pago.models import MedioPago, Pago
from venta.models import Venta

logger = logging.getLogger(__name__)

# Correos generados en mostrador sin buzón real — no enviar para evitar rebotes.
_DOMINIOS_SIN_ENVIO = ("@technova-pos.local",)


def _correo_enviable(correo: str) -> bool:
    c = (correo or "").strip().lower()
    if not c or "@" not in c:
        return False
    return not any(dom in c for dom in _DOMINIOS_SIN_ENVIO)


def _etiqueta_metodo_pago(pago: Pago) -> str:
    mp = (
        MedioPago.objects.filter(pago=pago)
        .order_by("id")
        .values_list("metodo_pago", flat=True)
        .first()
    )
    if not mp:
        return "—"
    return dict(MedioPago.Metodo.choices).get(mp, mp)


def enviar_correo_compra_confirmada_cliente(
    *,
    venta_id: int,
    pago_id: int,
    canal: str = "online",
) -> None:
    """
    canal: 'online' (checkout) | 'punto_fisico' (empleado POS).
    No lanza excepción hacia el caller: errores solo en log.
    """
    try:
        venta = (
            Venta.objects.select_related("usuario", "empleado")
            .filter(pk=venta_id)
            .first()
        )
        pago = Pago.objects.filter(pk=pago_id).first()
        if not venta or not pago:
            logger.warning(
                "Correo compra: venta o pago no encontrado (venta_id=%s, pago_id=%s)",
                venta_id,
                pago_id,
            )
            return

        datos_fm = getattr(venta, "datos_facturacion_mostrador", None) or {}
        if datos_fm:
            nombre_saludo = (
                f"{datos_fm.get('nombres', '').strip()} {datos_fm.get('apellidos', '').strip()}"
            ).strip()
            cliente_ctx = SimpleNamespace(
                nombres=nombre_saludo or "Cliente",
                apellidos="",
            )
            correo = (datos_fm.get("correo_electronico") or "").strip()
        else:
            cliente_ctx = venta.usuario
            correo = (cliente_ctx.correo_electronico or "").strip()
        if not _correo_enviable(correo):
            logger.info(
                "Correo compra omitido (sin buzón válido): venta_id=%s correo=%r",
                venta_id,
                correo,
            )
            return

        lineas = [
            {
                "nombre": d.producto.nombre,
                "cantidad": d.cantidad,
                "precio_unitario": d.precio_unitario,
                "subtotal": d.precio_unitario * d.cantidad,
            }
            for d in venta.detalles.select_related("producto").all()
        ]

        base = (getattr(settings, "TECHNOVA_PUBLIC_URL", "") or "").strip().rstrip("/")
        if not base:
            base = "http://127.0.0.1:8000"
        tienda_url = f"{base}/"

        ctx = {
            "cliente": cliente_ctx,
            "venta": venta,
            "pago": pago,
            "lineas": lineas,
            "canal": canal,
            "metodo_pago": _etiqueta_metodo_pago(pago),
            "tienda_url": tienda_url,
        }

        html = render_to_string("correos/email_compra_confirmada.html", ctx)
        asunto = f"Tu compra en Technova #{venta.id} — Factura {pago.numero_factura}"
        texto_plano = (
            f"Hola {cliente_ctx.nombres},\n\n"
            f"Registramos tu compra #{venta.id}.\n"
            f"Factura: {pago.numero_factura}\n"
            f"Total: ${pago.monto}\n"
            f"Método de pago: {ctx['metodo_pago']}\n\n"
            f"Gracias por comprar en Technova.\n"
            f"{tienda_url}\n"
        )
        msg = EmailMultiAlternatives(
            subject=asunto,
            body=texto_plano,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[correo],
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
        logger.info("Correo compra confirmada enviado a %s (venta_id=%s)", correo, venta_id)
    except Exception:
        logger.exception(
            "Fallo al enviar correo de compra confirmada (venta_id=%s, pago_id=%s)",
            venta_id,
            pago_id,
        )
