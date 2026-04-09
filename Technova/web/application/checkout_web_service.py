import base64
import json
import uuid
from decimal import Decimal
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import redirect
from django.utils import timezone

from carrito.models import Carrito
from common.container import get_carrito_lineas_service, get_checkout_service
from envio.models import Transportadora
from pago.models import MedioPago
from usuario.infrastructure.models.usuario_model import Usuario

from web.domain.constants import (
    SESSION_CK_DIR,
    SESSION_CK_ENV,
    SESSION_CK_INFO,
    SESSION_CK_PAGO,
    SESSION_CK_PAYPAL,
    SESSION_CK_RESULT,
)


def carrito_activo_id(uid: int) -> int | None:
    c = (
        Carrito.objects.filter(usuario_id=uid, estado=Carrito.Estado.ACTIVO)
        .order_by("-fecha_creacion", "-id")
        .first()
    )
    return c.id if c else None


def checkout_carrito_tiene_items(uid: int) -> bool:
    return bool(get_carrito_lineas_service().listar_items(uid))


def transportadoras_para_checkout():
    qs = Transportadora.objects.filter(activo=True).order_by("nombre")
    if not qs.exists():
        try:
            Transportadora.objects.create(
                nombre="Servientrega",
                telefono="3000000000",
                correo_electronico="logistica-default@technova.internal",
                activo=True,
            )
        except IntegrityError:
            pass
        qs = Transportadora.objects.filter(activo=True).order_by("nombre")
    return qs


def metodos_pago_validos() -> set[str]:
    return {c[0] for c in MedioPago.Metodo.choices}


def carrito_productos_total_spring(uid: int) -> tuple[list[dict], Decimal]:
    """Ítems y total al estilo CarritoItemDto + precios del proyecto Spring."""
    items = get_carrito_lineas_service().listar_items(uid)
    productos: list[dict] = []
    total = Decimal("0")
    for it in items:
        pid = it["producto_id"]
        nombre = it["nombre_producto"]
        cant = int(it.get("cantidad", 1))
        pu = Decimal(it.get("precio_unitario", "0"))
        sub = pu * cant
        total += sub
        img = (it.get("imagen") or "").strip()
        productos.append(
            {
                "productoId": pid,
                "nombreProducto": nombre,
                "cantidad": cant,
                "imagen": img,
                "precioVenta": pu,
                "precio_linea": sub,
            }
        )
    return productos, total


def asegurar_transportadoras_spring() -> None:
    seed = [
        ("Servientrega", "logistica-servientrega@technova.internal"),
        ("Coordinadora", "logistica-coordinadora@technova.internal"),
        ("Interrapidisimo", "logistica-interrapidisimo@technova.internal"),
    ]
    for nombre, email in seed:
        Transportadora.objects.get_or_create(
            nombre=nombre,
            defaults={
                "telefono": "3000000000",
                "correo_electronico": email,
                "activo": True,
            },
        )


def transportadora_por_nombre_spring(nombre: str) -> Transportadora | None:
    asegurar_transportadoras_spring()
    n = (nombre or "").strip()
    if not n:
        return None
    return Transportadora.objects.filter(nombre__iexact=n).first()


def map_metodo_pago_spring(m: str | None) -> str:
    """Alinea el método del checkout web con el catálogo de MedioPago (PayPal ≠ PSE)."""
    m = (m or "").strip()
    if m == "paypal_sandbox":
        return MedioPago.Metodo.PAYPAL.value
    if m in metodos_pago_validos():
        return m
    return MedioPago.Metodo.PSE.value


def paypal_client_id() -> str:
    return (getattr(settings, "TECHNOVA_PAYPAL_CLIENT_ID", "") or "").strip()


def paypal_client_secret() -> str:
    return (getattr(settings, "TECHNOVA_PAYPAL_CLIENT_SECRET", "") or "").strip()


def paypal_base_url() -> str:
    return (
        getattr(settings, "TECHNOVA_PAYPAL_BASE_URL", "")
        or "https://api-m.sandbox.paypal.com"
    ).rstrip("/")


def paypal_currency() -> str:
    raw = (getattr(settings, "TECHNOVA_PAYPAL_CURRENCY", "") or "USD").strip().upper()
    if raw == "COP":
        return "USD"
    return raw or "USD"


def paypal_is_configured() -> bool:
    return bool(paypal_client_id() and paypal_client_secret())


def paypal_fetch_access_token() -> str:
    basic_raw = f"{paypal_client_id()}:{paypal_client_secret()}".encode("utf-8")
    basic = base64.b64encode(basic_raw).decode("ascii")
    req = urllib_request.Request(
        f"{paypal_base_url()}/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        method="POST",
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            token = (payload.get("access_token") or "").strip()
            if not token:
                raise ValueError("PayPal no devolvio access_token")
            return token
    except (urllib_error.URLError, urllib_error.HTTPError, ValueError) as exc:
        raise ValueError(f"No se pudo obtener token de PayPal: {exc}") from exc


def paypal_create_order(
    *,
    amount: Decimal,
    reference_code: str,
    customer_email: str,
    return_url: str,
    cancel_url: str,
) -> tuple[str, str]:
    token = paypal_fetch_access_token()
    total = str(amount.quantize(Decimal("0.01")))
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": reference_code,
                "amount": {"currency_code": paypal_currency(), "value": total},
            }
        ],
        "payer": {"email_address": customer_email} if customer_email else {},
        "application_context": {
            "brand_name": "TechNova",
            "user_action": "PAY_NOW",
            "return_url": return_url,
            "cancel_url": cancel_url,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        f"{paypal_base_url()}/v2/checkout/orders",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            order_id = (body.get("id") or "").strip()
            approval_url = ""
            for link in body.get("links", []):
                if (link.get("rel") or "").lower() == "approve":
                    approval_url = (link.get("href") or "").strip()
                    break
            if not order_id or not approval_url:
                raise ValueError("PayPal no devolvio orderId o approveUrl")
            return order_id, approval_url
    except (urllib_error.URLError, urllib_error.HTTPError, ValueError) as exc:
        raise ValueError(f"No se pudo crear orden en PayPal: {exc}") from exc


def paypal_capture_order(order_id: str) -> tuple[bool, str]:
    if not order_id:
        return False, "INVALID_ORDER_ID"
    token = paypal_fetch_access_token()
    encoded_order_id = urllib_parse.quote(order_id, safe="")
    req = urllib_request.Request(
        f"{paypal_base_url()}/v2/checkout/orders/{encoded_order_id}/capture",
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            status = (body.get("status") or "").strip().upper()
            return status == "COMPLETED", (status or "UNKNOWN")
    except urllib_error.HTTPError as exc:
        # PayPal puede responder 422 cuando el order ya fue capturado previamente
        # (p. ej. usuario recarga la URL de retorno). En ese caso, consultamos el estado.
        if getattr(exc, "code", None) == 422:
            try:
                req_status = urllib_request.Request(
                    f"{paypal_base_url()}/v2/checkout/orders/{encoded_order_id}",
                    method="GET",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                )
                with urllib_request.urlopen(req_status, timeout=20) as resp2:
                    body2 = json.loads(resp2.read().decode("utf-8"))
                    status2 = (body2.get("status") or "").strip().upper()
                    if status2 == "COMPLETED":
                        return True, "COMPLETED"
                    return False, f"HTTP_422_{status2 or 'UNKNOWN'}"
            except Exception:  # noqa: BLE001
                return False, "HTTP_422"
        return False, f"HTTP_{exc.code}"
    except urllib_error.URLError:
        return False, "NETWORK_ERROR"


def limpiar_sesion_checkout(request) -> None:
    for key in (SESSION_CK_INFO, SESSION_CK_DIR, SESSION_CK_ENV, SESSION_CK_PAGO):
        request.session.pop(key, None)


def doc_tipo_checkout(usuario: Usuario, info: dict) -> str:
    raw = (info.get("documentType") or usuario.tipo_documento or "CC").strip().upper()
    if raw in ("CC", "CE", "PAS"):
        return raw
    return "CC"


def ejecutar_checkout_desde_sesion(request, uid: int):
    info = request.session.get(SESSION_CK_INFO) or {}
    dire = request.session.get(SESSION_CK_DIR) or {}
    env = request.session.get(SESSION_CK_ENV) or {}
    pago = request.session.get(SESSION_CK_PAGO) or {}
    if not info or not dire or not env or not pago:
        messages.error(request, "Datos de checkout incompletos. Vuelve a empezar.")
        return redirect("web_cliente_checkout_info")
    carrito_id = carrito_activo_id(uid)
    if not carrito_id:
        messages.error(request, "No hay carrito activo.")
        return redirect("web_carrito")
    try:
        u = Usuario.objects.get(pk=uid)
        if info.get("firstName"):
            u.nombres = info["firstName"][:120]
        if info.get("lastName"):
            u.apellidos = info["lastName"][:120]
        if info.get("phone"):
            u.telefono = info["phone"][:20]
        partes_dir = [
            dire.get("direccion"),
            dire.get("barrio"),
            dire.get("localidad"),
            dire.get("ciudad"),
            dire.get("departamento"),
        ]
        texto_dir = ", ".join(p for p in partes_dir if p)
        if texto_dir:
            u.direccion = texto_dir[:2000]
        u.save(update_fields=["nombres", "apellidos", "telefono", "direccion", "actualizado_en"])
    except Exception:  # noqa: BLE001
        pass
    t = transportadora_por_nombre_spring(env.get("transportadora", ""))
    if t is None:
        t = transportadoras_para_checkout().first()
    if t is None:
        messages.error(request, "No hay transportadora configurada. Contacta al administrador.")
        return redirect("web_cliente_checkout_revision")
    numero_guia = f"WEB-{uuid.uuid4().hex[:12].upper()}"
    costo_envio = Decimal("0")
    metodo_pago = map_metodo_pago_spring(pago.get("metodoPago"))
    numero_factura = f"FACT-{timezone.localdate().year}-{uid}-{uuid.uuid4().hex[:14].upper()}"
    try:
        resultado = get_checkout_service().ejecutar_checkout(
            usuario_id=uid,
            carrito_id=carrito_id,
            metodo_pago=metodo_pago,
            numero_factura=numero_factura,
            fecha_factura=timezone.localdate(),
            transportadora_id=t.id,
            numero_guia=numero_guia,
            costo_envio=costo_envio,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("web_cliente_checkout_revision")
    except IntegrityError:
        messages.error(request, "No se pudo registrar el pedido. Intentalo de nuevo.")
        return redirect("web_cliente_checkout_revision")
    limpiar_sesion_checkout(request)
    request.session.pop(SESSION_CK_PAYPAL, None)
    request.session[SESSION_CK_RESULT] = {
        "venta_id": resultado.venta_id,
        "total": str(resultado.total),
        "idempotente": resultado.idempotente,
    }
    request.session.modified = True
    return redirect("web_cliente_checkout_confirmacion")
