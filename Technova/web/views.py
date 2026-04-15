import json
import logging
import re
import uuid
import base64
from io import BytesIO
from pathlib import Path
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from xml.sax.saxutils import escape as _xml_escape

from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import CharField, Count, DecimalField, ExpressionWrapper, F, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDay
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.safestring import mark_safe
from django.urls import reverse

from carrito.models import Carrito, Favorito
from atencion_cliente.models import AtencionCliente
from common.container import (
    get_atencion_query_service,
    get_carrito_lineas_service,
    get_carrito_query_service,
    get_checkout_service,
    get_mensajeria_query_service,
    get_producto_service,
    get_proveedor_service,
    get_venta_query_service,
)
from compra.models import Compra, DetalleCompra
from envio.models import Envio, Transportadora
from mensajeria.models import MensajeDirecto, Notificacion
from pago.models import MedioPago, MetodoPagoUsuario, Pago
from producto.domain.entities import ProductoEntidad
from producto.models import Producto, ProductoCatalogoExtra, ProductoImagen
from producto.stock_niveles import (
    STOCK_BAJO_MAX,
    normalizar_nivel_stock_param,
    q_filtro_listado_nivel_stock,
)
from proveedor.domain.entities import ProveedorEntidad
from proveedor.models import Proveedor
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.application.registro_usuario_service import registrar_usuario_desde_payload
from usuario.application.use_cases.autenticacion_usecases import credenciales_coinciden
from usuario.infrastructure.models.usuario_model import Usuario
from venta.models import Venta
from venta.models import DetalleVenta
from web.application.admin_web_service import producto_modal_dict  # ✅ AGREGAR IMPORTACIÓN FALTANTE
from web.application.checkout_web_service import (
    paypal_create_order,
    paypal_is_configured,
)
from web.application.pos_cliente_service import resolver_cliente_para_pos
from web.application.producto_excel_import import (
    ErrorImportacionExcel,
    importar_productos_desde_bytes,
    respuesta_plantilla_excel,
)
from web.adapters.http import views_empleado as _empleado_pos_views

logger = logging.getLogger(__name__)

FACTURA_VENTA_PATTERN = re.compile(r"^FACT-\d+-(\d+)$", re.IGNORECASE)
# Mismas claves de sesión que Spring: checkout_informacion, checkout_direccion, etc.
SESSION_CK_INFO = "checkout_informacion"
SESSION_CK_DIR = "checkout_direccion"
SESSION_CK_ENV = "checkout_envio"
SESSION_CK_PAGO = "checkout_pago"
SESSION_CK_RESULT = "checkout_resultado"
SESSION_CK_PAYPAL = "checkout_paypal"


def _carrito_activo_id(uid: int) -> int | None:
    c = (
        Carrito.objects.filter(usuario_id=uid, estado=Carrito.Estado.ACTIVO)
        .order_by("-fecha_creacion", "-id")
        .first()
    )
    return c.id if c else None


def _checkout_carrito_tiene_items(uid: int) -> bool:
    return bool(get_carrito_lineas_service().listar_items(uid))


def _carrito_preview_para_usuario(uid: int | None) -> list[dict]:
    """Vista previa del carrito (máx. 8 líneas) para el panel del header y respuestas JSON."""
    if not uid:
        return []
    out: list[dict] = []
    for it in get_carrito_lineas_service().listar_items(uid)[:8]:
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


def _transportadoras_para_checkout():
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


def _metodos_pago_validos() -> set[str]:
    return {c[0] for c in MedioPago.Metodo.choices}


def _carrito_productos_total_spring(uid: int) -> tuple[list[dict], Decimal]:
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


def _asegurar_transportadoras_spring() -> None:
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


def _transportadora_por_nombre_spring(nombre: str) -> Transportadora | None:
    _asegurar_transportadoras_spring()
    n = (nombre or "").strip()
    if not n:
        return None
    return Transportadora.objects.filter(nombre__iexact=n).first()


def _map_metodo_pago_spring(m: str | None) -> str:
    """Alinea el método del checkout web con el catálogo de MedioPago (PayPal ≠ PSE)."""
    m = (m or "").strip()
    if m == "paypal_sandbox":
        return MedioPago.Metodo.PAYPAL.value
    if m in _metodos_pago_validos():
        return m
    return MedioPago.Metodo.PSE.value


def _paypal_client_id() -> str:
    return (getattr(settings, "TECHNOVA_PAYPAL_CLIENT_ID", "") or "").strip()


def _paypal_client_secret() -> str:
    return (getattr(settings, "TECHNOVA_PAYPAL_CLIENT_SECRET", "") or "").strip()


def _paypal_base_url() -> str:
    return (
        getattr(settings, "TECHNOVA_PAYPAL_BASE_URL", "")
        or "https://api-m.sandbox.paypal.com"
    ).rstrip("/")


def _paypal_currency() -> str:
    raw = (getattr(settings, "TECHNOVA_PAYPAL_CURRENCY", "") or "USD").strip().upper()
    if raw == "COP":
        return "USD"
    return raw or "USD"


def _paypal_is_configured() -> bool:
    return bool(_paypal_client_id() and _paypal_client_secret())


def _paypal_fetch_access_token() -> str:
    basic_raw = f"{_paypal_client_id()}:{_paypal_client_secret()}".encode("utf-8")
    basic = base64.b64encode(basic_raw).decode("ascii")
    req = urllib_request.Request(
        f"{_paypal_base_url()}/v1/oauth2/token",
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


def _paypal_create_order(
    *,
    amount: Decimal,
    reference_code: str,
    customer_email: str,
    return_url: str,
    cancel_url: str,
) -> tuple[str, str]:
    token = _paypal_fetch_access_token()
    total = str(amount.quantize(Decimal("0.01")))
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "reference_id": reference_code,
                "amount": {"currency_code": _paypal_currency(), "value": total},
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
        f"{_paypal_base_url()}/v2/checkout/orders",
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


def _paypal_capture_order(order_id: str) -> tuple[bool, str]:
    if not order_id:
        return False, "INVALID_ORDER_ID"
    token = _paypal_fetch_access_token()
    encoded_order_id = urllib_parse.quote(order_id, safe="")
    req = urllib_request.Request(
        f"{_paypal_base_url()}/v2/checkout/orders/{encoded_order_id}/capture",
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
        # PayPal puede responder 422 si el order ya fue capturado (recarga / doble submit).
        if getattr(exc, "code", None) == 422:
            try:
                req_status = urllib_request.Request(
                    f"{_paypal_base_url()}/v2/checkout/orders/{encoded_order_id}",
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


def _aplicar_usuario_desde_checkout_sesion(uid: int, info: dict, dire: dict) -> None:
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


def _numero_factura_desde_paypal_order(order_id: str, uid: int) -> str | None:
    """
    Número de factura estable a partir del order ID de PayPal y el usuario.
    Permite idempotencia si el cliente vuelve a cargar la URL de retorno tras un pago capturado.
    Máximo 50 caracteres (límite del modelo Pago).
    """
    safe = "".join(c for c in (order_id or "") if c.isalnum())
    if not safe:
        return None
    base = f"FACT-PP-{uid}-{safe}"
    return base[:50]


def _ejecutar_checkout_desde_sesion(request, uid: int, *, numero_factura: str | None = None):
    info = request.session.get(SESSION_CK_INFO) or {}
    dire = request.session.get(SESSION_CK_DIR) or {}
    env = request.session.get(SESSION_CK_ENV) or {}
    pago = request.session.get(SESSION_CK_PAGO) or {}
    if not info or not dire or not env or not pago:
        messages.error(request, "Datos de checkout incompletos. Vuelve a empezar.")
        return redirect("web_cliente_checkout_info")
    carrito_id = _carrito_activo_id(uid)
    if not carrito_id:
        messages.error(request, "No hay carrito activo.")
        return redirect("web_carrito")
    _aplicar_usuario_desde_checkout_sesion(uid, info, dire)
    t = _transportadora_por_nombre_spring(env.get("transportadora", ""))
    if t is None:
        t = _transportadoras_para_checkout().first()
    if t is None:
        messages.error(request, "No hay transportadora configurada. Contacta al administrador.")
        return redirect("web_cliente_checkout_revision")
    numero_guia = f"WEB-{uuid.uuid4().hex[:12].upper()}"
    costo_envio = Decimal("0")
    metodo_pago = _map_metodo_pago_spring(pago.get("metodoPago"))
    if numero_factura is None:
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
    except IntegrityError as exc:
        logger.exception(
            "Checkout IntegrityError (uid=%s carrito_id=%s factura=%s): %s",
            uid,
            carrito_id,
            numero_factura,
            exc,
        )
        msg = (
            "No se pudo registrar el pedido en la base de datos. "
            "Si el cargo ya apareció en PayPal o en tu banco, guarda el comprobante y contacta soporte; "
            "no vuelvas a pagar hasta confirmar."
        )
        if settings.DEBUG:
            msg = f"{msg} [DEBUG: {exc}]"
        messages.error(request, msg)
        return redirect("web_cliente_checkout_revision")
    _limpiar_sesion_checkout(request)
    request.session.pop(SESSION_CK_PAYPAL, None)
    request.session[SESSION_CK_RESULT] = {
        "venta_id": resultado.venta_id,
        "total": str(resultado.total),
        "idempotente": resultado.idempotente,
    }
    request.session.modified = True
    return redirect("web_cliente_checkout_confirmacion")


def _limpiar_sesion_checkout(request) -> None:
    for key in (SESSION_CK_INFO, SESSION_CK_DIR, SESSION_CK_ENV, SESSION_CK_PAGO):
        request.session.pop(key, None)


def _doc_tipo_checkout(usuario: Usuario, info: dict) -> str:
    raw = (info.get("documentType") or usuario.tipo_documento or "CC").strip().upper()
    if raw in ("CC", "CE", "PAS"):
        return raw
    return "CC"


def _parse_date_param(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _extraer_venta_id_factura(numero_factura: str | None) -> int | None:
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


def _venta_cliente_desde_pago(pago: Pago) -> tuple[Venta | None, Usuario | None]:
    medios = list(pago.medios_pago.all())
    if medios:
        venta = medios[0].detalle_venta.venta
        return venta, venta.usuario
    vid = _extraer_venta_id_factura(pago.numero_factura)
    if vid:
        venta = (
            Venta.objects.select_related("usuario", "empleado", "administrador")
            .filter(pk=vid)
            .first()
        )
        if venta:
            return venta, venta.usuario
    return None, None


def _badge_clase_estado_pago(estado: str) -> str:
    e = (estado or "").lower()
    if e == Pago.EstadoPago.APROBADO:
        return "confirmado"
    if e == Pago.EstadoPago.PENDIENTE:
        return "pendiente"
    if e in (Pago.EstadoPago.RECHAZADO, Pago.EstadoPago.REEMBOLSADO):
        return "cancelado"
    return "pendiente"


def _fecha_larga_es(d: date | None) -> str:
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


def _etiqueta_medio_pago_mostrar(medio: MedioPago | None) -> str:
    """Texto mostrado en admin (corrige etiqueta PSE cuando el pago fue PayPal en checkout web)."""
    if medio is None:
        return ""
    if medio.metodo_pago == MedioPago.Metodo.PSE.value and getattr(
        settings, "TECHNOVA_ADMIN_PSE_LEGACY_COMO_PAYPAL", True
    ):
        return "PayPal"
    return medio.get_metodo_pago_display()


def _lista_metodos_pago_display(pago: Pago) -> list[str]:
    """Etiquetas legibles únicas (por código de método) según medios asociados al pago."""
    seen: set[str] = set()
    out: list[str] = []
    for m in pago.medios_pago.all():
        if m.metodo_pago not in seen:
            seen.add(m.metodo_pago)
            out.append(_etiqueta_medio_pago_mostrar(m))
    return out


def _filtrar_queryset_pagos_por_estado_get(qs, estado_raw: str | None):
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


def _wants_json_response(request) -> bool:
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or (request.headers.get("Accept") or "").startswith("application/json")
        or (request.content_type or "").startswith("application/json")
    )


def _cliente_login_required(view_func):
    """Solo usuarios con sesión Django (misma clave que login_web)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get(SESSION_USUARIO_ID):
            return redirect("web_login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _admin_login_required(view_func):
    """Sesión activa y rol administrador."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        uid = request.session.get(SESSION_USUARIO_ID)
        if not uid:
            return redirect("web_login")
        try:
            usuario = Usuario.objects.get(pk=uid)
        except Usuario.DoesNotExist:
            request.session.flush()
            return redirect("web_login")
        if usuario.rol != Usuario.Rol.ADMIN:
            return redirect("inicio_autenticado")
        return view_func(request, *args, **kwargs)

    return _wrapped


def _empleado_login_required(view_func):
    """Sesión activa y rol empleado (panel propio; admin y cliente redirigen)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        uid = request.session.get(SESSION_USUARIO_ID)
        if not uid:
            return redirect("web_login")
        try:
            usuario = Usuario.objects.get(pk=uid)
        except Usuario.DoesNotExist:
            request.session.flush()
            return redirect("web_login")
        if usuario.rol == Usuario.Rol.ADMIN:
            return redirect("web_admin_perfil")
        if usuario.rol != Usuario.Rol.EMPLEADO:
            return redirect("inicio_autenticado")
        return view_func(request, *args, **kwargs)

    return _wrapped


EMPLEADO_SECCIONES: dict[str, str] = {
    "inicio": "Panel de empleado",
    "perfil": "Mi perfil",
    "usuarios": "Usuarios",
    "productos": "Visualización de artículos",
    "punto-venta": "Punto de venta",
    "pedidos": "Pedidos",
    "atencion-cliente": "Atención al cliente",
    "reclamos": "Reclamos",
    "notificaciones": "Notificaciones",
}


@_empleado_login_required
def empleado_dashboard(request, seccion: str = "inicio"):
    """Shell del panel empleado (misma base visual que admin); módulos sin implementar."""
    if seccion == "mensajes":
        return redirect("web_empleado_mensajes")
    if seccion == "notificaciones":
        return redirect("web_empleado_notificaciones")
    if seccion not in EMPLEADO_SECCIONES:
        return redirect("web_empleado_inicio")
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)
    ctx = {
        "usuario": usuario,
        "seccion": seccion,
        "titulo_seccion": EMPLEADO_SECCIONES[seccion],
    }

    if seccion == "usuarios":
        busqueda = (request.GET.get("busqueda") or "").strip()
        # En panel empleado solo se visualiza información de clientes.
        qs_usuarios = Usuario.objects.filter(rol=Usuario.Rol.CLIENTE).order_by("id")
        if busqueda:
            qs_usuarios = qs_usuarios.filter(
                Q(nombres__icontains=busqueda)
                | Q(apellidos__icontains=busqueda)
                | Q(correo_electronico__icontains=busqueda)
                | Q(numero_documento__icontains=busqueda)
            )
        ctx.update(
            {
                "busqueda": busqueda,
                "usuarios_lista": list(qs_usuarios[:400]),
                "total_clientes": Usuario.objects.filter(rol=Usuario.Rol.CLIENTE).count(),
                "clientes_activos": Usuario.objects.filter(
                    rol=Usuario.Rol.CLIENTE, activo=True
                ).count(),
                "clientes_inactivos": Usuario.objects.filter(
                    rol=Usuario.Rol.CLIENTE, activo=False
                ).count(),
            }
        )
    elif seccion == "atencion-cliente":
        estado = (request.GET.get("estado") or "todas").strip().lower()
        busqueda = (request.GET.get("busqueda") or "").strip()

        # Tickets (todas las solicitudes; filtros como Java)
        tickets_raw = get_atencion_query_service().listar_solicitudes(None) or []

        # Mapa de nombres por usuario_id (para mostrar "cliente" en empleado)
        user_ids = sorted({int(t.get("usuario_id")) for t in tickets_raw if t.get("usuario_id")})
        usuarios_map = {
            u.id: f"{u.nombres} {u.apellidos}".strip()
            for u in Usuario.objects.filter(id__in=user_ids).only("id", "nombres", "apellidos")
        }

        def ticket_resuelto(t: dict) -> bool:
            return bool((t.get("respuesta") or "").strip())

        # aplicar filtros
        tickets_filtrados = []
        for t in tickets_raw:
            uid_t = t.get("usuario_id")
            nombre = usuarios_map.get(uid_t, f"Usuario ID: {uid_t}" if uid_t else "Usuario desconocido")
            if busqueda and busqueda.lower() not in nombre.lower():
                continue
            est = (t.get("estado") or "").lower()
            if estado == "todas":
                pass
            elif estado == "pendientes":
                if est not in ("abierta", "en_proceso"):
                    continue
            elif estado == "en_proceso":
                if est != "en_proceso" or ticket_resuelto(t):
                    continue
            elif estado == "resuelto":
                if not ticket_resuelto(t):
                    continue
            elif estado == "cerrado":
                if est != "cerrada":
                    continue
            tickets_filtrados.append(
                {
                    "id": t.get("id"),
                    "usuarioId": uid_t,
                    "tema": t.get("tema") or "",
                    "descripcion": t.get("descripcion") or "",
                    "fechaConsulta": t.get("fechaConsulta") or t.get("fecha_consulta"),
                    "respuesta": t.get("respuesta") or "",
                    "estado": (t.get("estado") or "").strip().lower(),
                    "clienteNombre": nombre,
                }
            )

        # Stats (consultas)
        total_consultas = AtencionCliente.objects.count()
        pendientes = AtencionCliente.objects.filter(
            estado__in=[AtencionCliente.Estado.ABIERTA, AtencionCliente.Estado.EN_PROCESO]
        ).count()

        # Conversaciones (último mensaje por conversación)
        md_items = get_mensajeria_query_service().listar_mensajes_directos_todos() or []
        por_conv: dict[str, dict] = {}
        for m in md_items:
            cid = m.get("conversationId")
            if not cid:
                continue
            prev = por_conv.get(cid)
            if prev is None or (m.get("createdAt") or "") > (prev.get("createdAt") or ""):
                por_conv[cid] = m
        conversaciones = sorted(por_conv.values(), key=lambda x: x.get("createdAt") or "", reverse=True)

        # nombres para conversaciones (del remitente cliente)
        conv_user_ids = sorted(
            {
                int(c.get("senderId"))
                for c in conversaciones
                if c.get("senderType") == "cliente" and c.get("senderId")
            }
        )
        conv_usuarios_map = {
            u.id: f"{u.nombres} {u.apellidos}".strip()
            for u in Usuario.objects.filter(id__in=conv_user_ids).only("id", "nombres", "apellidos")
        }

        conversaciones_norm = []
        for c in conversaciones:
            user_id = c.get("senderId")
            nombre_c = conv_usuarios_map.get(user_id, f"Usuario ID: {user_id}" if user_id else "Usuario desconocido")
            if busqueda and busqueda.lower() not in nombre_c.lower():
                continue
            conversaciones_norm.append(
                {
                    "conversationId": c.get("conversationId"),
                    "id": c.get("id"),
                    "userId": user_id,
                    "asunto": c.get("subject") or "",
                    "mensaje": c.get("message") or "",
                    "prioridad": c.get("priority") or "normal",
                    "estado": c.get("state") or "enviado",
                    "isRead": bool(c.get("isRead")),
                    "senderType": c.get("senderType"),
                    "createdAt": c.get("createdAt"),
                    "clienteNombre": nombre_c,
                }
            )

        md_stats = get_mensajeria_query_service().estadisticas_mensajes_directos()
        mensajes = md_stats.get("mensajes", 0)
        no_leidos = md_stats.get("noLeidos", 0)

        ctx.update(
            {
                "estado": estado,
                "busqueda": busqueda,
                "tickets": tickets_filtrados,
                "conversaciones": conversaciones_norm,
                "totalConsultas": total_consultas,
                "pendientes": pendientes,
                "mensajes": mensajes,
                "noLeidos": no_leidos,
                "nombresUsuarios": usuarios_map,
            }
        )
    elif seccion == "reclamos":
        estado = (request.GET.get("estado") or "todos").strip().lower()
        busqueda = (request.GET.get("busqueda") or "").strip()

        reclamos_raw = get_atencion_query_service().listar_reclamos(None) or []
        user_ids = sorted(
            {
                int(r.get("usuarioId") or r.get("usuario_id"))
                for r in reclamos_raw
                if (r.get("usuarioId") or r.get("usuario_id"))
            }
        )
        usuarios_map = {
            u.id: f"{u.nombres} {u.apellidos}".strip()
            for u in Usuario.objects.filter(id__in=user_ids).only("id", "nombres", "apellidos")
        }

        reclamos_filtrados = []
        for r in reclamos_raw:
            uid_r = r.get("usuarioId") or r.get("usuario_id")
            nombre = usuarios_map.get(
                uid_r, f"Usuario ID: {uid_r}" if uid_r else "Usuario desconocido"
            )
            texto = f"{nombre} {r.get('titulo','')} {r.get('descripcion','')}".lower()
            if busqueda and busqueda.lower() not in texto:
                continue
            est = (r.get("estado") or "").lower()
            if estado != "todos" and est != estado:
                continue
            item = dict(r)
            item["clienteNombre"] = nombre
            reclamos_filtrados.append(item)

        ctx.update(
            {
                "estado": estado,
                "busqueda": busqueda,
                "reclamos": reclamos_filtrados,
                "nombresUsuarios": usuarios_map,
            }
        )
    elif seccion == "productos":
        categoria = (request.GET.get("categoria") or "").strip()
        busqueda = (request.GET.get("busqueda") or "").strip()
        qs_productos = Producto.objects.select_related("proveedor").order_by("-id")
        if categoria:
            qs_productos = qs_productos.filter(categoria__iexact=categoria)
        if busqueda:
            qs_productos = qs_productos.filter(
                Q(nombre__icontains=busqueda) | Q(codigo__icontains=busqueda)
            )
        ctx.update(
            {
                "categoria": categoria,
                "busqueda": busqueda,
                "productos_lista": list(qs_productos[:500]),
                "categorias_opts": sorted(
                    set(
                        Producto.objects.exclude(categoria="")
                        .values_list("categoria", flat=True)
                        .distinct()
                    ),
                    key=str.lower,
                ),
                "total_productos": Producto.objects.count(),
                "productos_bajo_stock": Producto.objects.filter(
                    activo=True, stock__gte=1, stock__lte=STOCK_BAJO_MAX
                ).count(),
                "productos_agotados": Producto.objects.filter(activo=True, stock=0).count(),
            }
        )
    elif seccion == "pedidos":
        busqueda = (request.GET.get("busqueda") or "").strip()
        usuario_id = (request.GET.get("usuarioId") or "").strip()
        fecha_desde = (request.GET.get("fechaDesde") or "").strip()
        fecha_hasta = (request.GET.get("fechaHasta") or "").strip()
        producto = (request.GET.get("producto") or "").strip()
        estado = (request.GET.get("estado") or "").strip().lower()

        qs_ventas = Venta.objects.select_related("usuario").order_by("-fecha_venta", "-id")
        if usuario_id.isdigit():
            qs_ventas = qs_ventas.filter(usuario_id=int(usuario_id))
        if fecha_desde:
            f_desde = _parse_date_param(fecha_desde)
            if f_desde:
                qs_ventas = qs_ventas.filter(fecha_venta__gte=f_desde)
            else:
                fecha_desde = ""
        if fecha_hasta:
            f_hasta = _parse_date_param(fecha_hasta)
            if f_hasta:
                qs_ventas = qs_ventas.filter(fecha_venta__lte=f_hasta)
            else:
                fecha_hasta = ""
        if producto:
            qs_ventas = qs_ventas.filter(detalles__producto__nombre__icontains=producto).distinct()
        if estado in {Venta.Estado.ABIERTA, Venta.Estado.FACTURADA, Venta.Estado.ANULADA}:
            qs_ventas = qs_ventas.filter(estado=estado)
        else:
            estado = ""
        if busqueda:
            if busqueda.isdigit():
                qs_ventas = qs_ventas.filter(id=int(busqueda))
            else:
                qs_ventas = qs_ventas.filter(
                    Q(usuario__nombres__icontains=busqueda)
                    | Q(usuario__apellidos__icontains=busqueda)
                    | Q(usuario__correo_electronico__icontains=busqueda)
                )

        hoy = timezone.localdate()
        ctx.update(
            {
                "busqueda": busqueda,
                "usuario_id": usuario_id,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
                "producto": producto,
                "estado": estado,
                "ventas_lista": list(qs_ventas[:700]),
                "usuarios_filtro": list(
                    Usuario.objects.filter(ventas__isnull=False)
                    .distinct()
                    .order_by("nombres", "apellidos")
                ),
                "total_pedidos": Venta.objects.count(),
                "total_ventas_monto": Venta.objects.aggregate(s=Sum("total"))["s"]
                or Decimal("0"),
                "pedidos_este_mes": Venta.objects.filter(
                    fecha_venta__year=hoy.year, fecha_venta__month=hoy.month
                ).count(),
            }
        )
    elif seccion == "punto-venta":
        ctx["productos"] = list(
            Producto.objects.filter(activo=True, stock__gt=0).order_by("nombre", "id")[:500]
        )
        ctx["clientes"] = list(
            Usuario.objects.filter(rol=Usuario.Rol.CLIENTE, activo=True)
            .order_by("nombres", "apellidos", "id")[:500]
        )

        if request.method == "POST":
            accion = (request.POST.get("accion") or "").strip().lower()
            try:
                items = _empleado_pos_views._pos_parse_items(request.POST.get("items_json") or "[]")
            except (ValueError, json.JSONDecodeError) as exc:
                messages.error(request, str(exc))
                return redirect("web_empleado_seccion", seccion="punto-venta")

            cliente_id, datos_mostrador, err_cliente = resolver_cliente_para_pos(request)
            if err_cliente:
                messages.error(request, err_cliente)
                return redirect("web_empleado_seccion", seccion="punto-venta")

            if accion not in ("efectivo", "paypal"):
                messages.error(request, "Selecciona un método de pago.")
                return redirect("web_empleado_seccion", seccion="punto-venta")

            if accion == "paypal" and datos_mostrador is not None:
                em = (datos_mostrador.get("correo_electronico") or "").strip()
                if not em or "@" not in em:
                    messages.error(
                        request,
                        "Para cobrar con PayPal ingresa el correo electrónico del comprador.",
                    )
                    return redirect("web_empleado_seccion", seccion="punto-venta")

            numero_factura = _empleado_pos_views._pos_numero_factura(cliente_id)
            cliente_obj = Usuario.objects.filter(pk=cliente_id).first()
            if datos_mostrador is not None:
                email_paypal = (datos_mostrador.get("correo_electronico") or "").strip()
            else:
                email_paypal = (cliente_obj.correo_electronico or "").strip() if cliente_obj else ""

            if accion == "paypal":
                if not paypal_is_configured():
                    messages.error(request, "PayPal no está configurado.")
                    return redirect("web_empleado_seccion", seccion="punto-venta")

                total = Decimal("0")
                for it in items:
                    p = Producto.objects.filter(pk=it["producto_id"], activo=True).first()
                    if not p or p.stock < it["cantidad"]:
                        messages.error(request, "Stock insuficiente o producto no disponible.")
                        return redirect("web_empleado_seccion", seccion="punto-venta")
                    total += (p.precio_publico or Decimal("0")) * int(it["cantidad"])

                try:
                    order_id, approval_url = paypal_create_order(
                        amount=total,
                        reference_code=numero_factura,
                        customer_email=email_paypal,
                        return_url=request.build_absolute_uri(reverse("web_empleado_pos_paypal_retorno")),
                        cancel_url=request.build_absolute_uri(reverse("web_empleado_punto_venta")),
                    )
                except ValueError as exc:
                    messages.error(request, str(exc))
                    return redirect("web_empleado_seccion", seccion="punto-venta")

                request.session["pos_paypal"] = {
                    "cliente_id": cliente_id,
                    "items": items,
                    "numero_factura": numero_factura,
                    "order_id": order_id,
                    "datos_facturacion_mostrador": datos_mostrador,
                }
                request.session.modified = True
                return redirect(approval_url)

            try:
                venta_id, _pago_id = _empleado_pos_views._pos_registrar_venta(
                    cliente_id=cliente_id,
                    items=items,
                    empleado_id=usuario.id,
                    metodo_pago=MedioPago.Metodo.EFECTIVO.value,
                    numero_factura=numero_factura,
                    datos_facturacion_mostrador=datos_mostrador,
                )
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect("web_empleado_seccion", seccion="punto-venta")

            messages.success(request, f"Venta registrada. Factura: {numero_factura}")
            return redirect("web_empleado_pos_factura", venta_id=venta_id)

    return render(request, "frontend/empleado/dashboard.html", ctx)


empleado_pos_paypal_retorno = _empleado_pos_views.empleado_pos_paypal_retorno
empleado_pos_factura = _empleado_pos_views.empleado_pos_factura


@_empleado_login_required
@require_http_methods(["GET", "POST"])
def empleado_notificaciones(request):
    """Notificaciones del sistema para el empleado en sesión (lectura + marcar leídas)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()
        svc = get_mensajeria_query_service()
        if accion == "marcar_leida":
            raw_id = request.POST.get("notificacion_id")
            try:
                nid = int(raw_id)
            except (TypeError, ValueError):
                messages.error(request, "Identificador de notificación no válido.")
                return redirect("web_empleado_notificaciones")
            if svc.marcar_notificacion_leida(usuario.id, nid):
                messages.success(request, "Notificación marcada como leída.")
            else:
                messages.error(request, "No se encontró la notificación o no te pertenece.")
            return redirect("web_empleado_notificaciones")
        if accion == "marcar_todas_leidas":
            n = svc.marcar_todas_notificaciones_leidas(usuario.id)
            messages.success(request, f"Se marcaron {n} notificación(es) como leídas.")
            return redirect("web_empleado_notificaciones")
        messages.error(request, "Acción no reconocida.")
        return redirect("web_empleado_notificaciones")

    leida_filtro = (request.GET.get("leida") or "").strip().lower()
    q = (request.GET.get("q") or "").strip()

    svc = get_mensajeria_query_service()
    if leida_filtro == "si":
        items = svc.listar_notificaciones_filtradas(usuario.id, leida=True)
    elif leida_filtro == "no":
        items = svc.listar_notificaciones_filtradas(usuario.id, leida=False)
    else:
        items = svc.listar_notificaciones_filtradas(usuario.id)
    if q:
        ql = q.lower()
        items = [
            it
            for it in items
            if ql in (it.get("titulo") or "").lower() or ql in (it.get("mensaje") or "").lower()
        ]

    total_recibidas = len(svc.listar_notificaciones_filtradas(usuario.id))
    total_no_leidas = len(svc.listar_notificaciones_filtradas(usuario.id, leida=False))

    return render(
        request,
        "frontend/empleado/notificaciones.html",
        {
            "usuario": usuario,
            "seccion": "notificaciones",
            "notificaciones": items[:500],
            "total_recibidas": total_recibidas,
            "total_no_leidas": total_no_leidas,
            "filtro_leida": leida_filtro,
            "filtro_q": q,
        },
    )


@_empleado_login_required
@require_http_methods(["GET"])
def empleado_notificaciones_poll(request):
    """JSON para actualizar el listado sin recargar (polling)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)
    leida_filtro = (request.GET.get("leida") or "").strip().lower()
    q = (request.GET.get("q") or "").strip()

    svc = get_mensajeria_query_service()
    if leida_filtro == "si":
        items = svc.listar_notificaciones_filtradas(usuario.id, leida=True)
    elif leida_filtro == "no":
        items = svc.listar_notificaciones_filtradas(usuario.id, leida=False)
    else:
        items = svc.listar_notificaciones_filtradas(usuario.id)
    if q:
        ql = q.lower()
        items = [
            it
            for it in items
            if ql in (it.get("titulo") or "").lower() or ql in (it.get("mensaje") or "").lower()
        ]

    total_recibidas = len(svc.listar_notificaciones_filtradas(usuario.id))
    total_no_leidas = len(svc.listar_notificaciones_filtradas(usuario.id, leida=False))

    # normalizar forma compatible con admin_poll
    out = [
        {
            "id": n.get("id"),
            "titulo": n.get("titulo"),
            "mensaje": n.get("mensaje"),
            "tipo": n.get("tipo"),
            "icono": n.get("icono") or "bell",
            "leida": bool(n.get("leida")),
            "fecha_creacion": n.get("fechaCreacion") or n.get("fecha_creacion"),
        }
        for n in items[:500]
    ]
    return JsonResponse(
        {
            "total_recibidas": total_recibidas,
            "total_no_leidas": total_no_leidas,
            "notificaciones": out,
        }
    )


@_empleado_login_required
@require_http_methods(["GET", "POST"])
def empleado_perfil_editar(request):
    """Edición de datos de contacto para empleados (ruta y plantilla distintas del cliente)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = get_object_or_404(Usuario, pk=uid)

    if request.method == "POST":
        telefono = (request.POST.get("telefono") or "").strip()
        direccion = (request.POST.get("direccion") or "").strip()
        current_password = request.POST.get("current_password") or ""
        if not credenciales_coinciden(current_password, usuario.contrasena_hash):
            messages.error(request, "La contraseña actual no es correcta.")
            return redirect("web_empleado_perfil_editar")
        cambios = []
        if usuario.telefono != telefono:
            cambios.append("teléfono")
        if usuario.direccion != direccion:
            cambios.append("dirección")
        usuario.telefono = telefono
        usuario.direccion = direccion
        usuario.save(update_fields=["telefono", "direccion", "actualizado_en"])
        if cambios:
            from mensajeria.services.notificaciones_admin import notificar_usuario_actualizado

            notificar_usuario_actualizado(
                usuario_id=usuario.id,
                correo=usuario.correo_electronico,
                cambios=cambios,
                origen="empleado_perfil",
            )
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect("web_empleado_seccion", seccion="perfil")

    return render(
        request,
        "frontend/empleado/perfil_editar.html",
        {"usuario": usuario, "seccion": "perfil"},
    )


def index_public(request):
    """Landing pública (invitado): catálogo, ofertas y enlaces a login/registro (`/`)."""
    from web.catalogo_nav import ctx_catalogo_index

    return render(
        request,
        "frontend/index_public.html",
        ctx_catalogo_index(),
    )


def root_entry(request):
    """Raíz `/`: con sesión → inicio, empleado, o perfil admin; sin sesión → index público."""
    uid = request.session.get(SESSION_USUARIO_ID)
    if uid:
        try:
            u = Usuario.objects.get(pk=uid)
            if u.rol == Usuario.Rol.ADMIN:
                return redirect("web_admin_perfil")
            if u.rol == Usuario.Rol.EMPLEADO:
                return redirect("web_empleado_inicio")
        except Usuario.DoesNotExist:
            pass
        return redirect("inicio_autenticado")
    return index_public(request)


@_cliente_login_required
def home(request):
    """Inicio autenticado / catálogo (`/inicio/`)."""
    from web.catalogo_nav import ctx_catalogo_index

    uid = request.session.get(SESSION_USUARIO_ID)
    if uid:
        try:
            u = Usuario.objects.get(pk=uid)
            if u.rol == Usuario.Rol.ADMIN:
                return redirect("web_admin_perfil")
            if u.rol == Usuario.Rol.EMPLEADO:
                return redirect("web_empleado_inicio")
        except Usuario.DoesNotExist:
            pass
    favoritos_qs = (
        Favorito.objects.select_related("producto")
        .filter(usuario_id=uid)
        .order_by("-id")[:8]
    )
    favoritos_preview = [
        {
            "id": f.producto.id,
            "nombre": f.producto.nombre,
            "imagen": f.producto.imagen_url or "",
            "precio": str(f.producto.precio_venta or "0"),
        }
        for f in favoritos_qs
    ]
    carrito_preview = _carrito_preview_para_usuario(uid)
    ctx = ctx_catalogo_index()
    ctx.update(
        {
            "usuario_id": uid,
            "favoritos_preview": favoritos_preview,
            "carrito_preview": carrito_preview,
        }
    )
    return render(request, "frontend/cliente/home.html", ctx)


@_cliente_login_required
@require_POST
def catalogo_agregar_carrito(request):
    """Agregar al carrito desde el catálogo (sesión Django + CSRF). Sin JWT."""
    uid = request.session.get(SESSION_USUARIO_ID)
    try:
        payload = json.loads(request.body.decode() or "{}")
        producto_id = int(payload.get("producto_id"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "message": "Solicitud inválida."}, status=400)
    try:
        get_carrito_lineas_service().agregar_producto(uid, producto_id, 1)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)
    return JsonResponse(
        {
            "ok": True,
            "message": "Producto agregado al carrito.",
            "carrito_preview": _carrito_preview_para_usuario(uid),
        }
    )


def _dashboard_fmt_rango_es(d0: date, d1: date) -> str:
    """Rango corto en español, p. ej. «27 mar – 2 abr 2026»."""
    meses = (
        "ene",
        "feb",
        "mar",
        "abr",
        "may",
        "jun",
        "jul",
        "ago",
        "sep",
        "oct",
        "nov",
        "dic",
    )
    m0, m1 = meses[d0.month - 1], meses[d1.month - 1]
    if d0.year == d1.year:
        if d0.month == d1.month:
            return f"{d0.day} – {d1.day} {m1} {d1.year}"
        return f"{d0.day} {m0} – {d1.day} {m1} {d1.year}"
    return f"{d0.day} {m0} {d0.year} – {d1.day} {m1} {d1.year}"


def _dashboard_bucket_categoria(categoria_raw: str | None) -> str:
    """
    Agrupa el texto libre de Producto.categoria para el gráfico de dona.
    (No existe modelo Pedido/DetallePedido de tienda: las líneas de venta son DetalleVenta.)
    """
    s = (categoria_raw or "").strip().lower()
    if not s:
        return "accesorios"
    s_norm = (
        s.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )
    cel_kw = (
        "celu",
        "phone",
        "smart",
        "movil",
        "iphone",
        "android",
        "tablet",
        "galaxy",
    )
    comp_kw = (
        "comput",
        "compu",
        "laptop",
        "noteb",
        "portatil",
        "pc",
        "desk",
        "torre",
        "macbook",
        "all-in",
        "allin",
        "workstation",
        "ultrabook",
        "escrit",
    )
    acc_kw = (
        "acces",
        "auricul",
        "audifon",
        "funda",
        "cable",
        "cargador",
        "parlant",
        "parlante",
        "mouse",
        "teclad",
        "protector",
        "vidrio",
        "adaptador",
        "usb",
        "hub",
        "memor",
        "power bank",
        "tripode",
    )
    if any(k in s_norm for k in cel_kw):
        return "celulares"
    if any(k in s_norm for k in comp_kw):
        return "computadores"
    if any(k in s_norm for k in acc_kw):
        return "accesorios"
    return "accesorios"


@_cliente_login_required
@require_POST
def catalogo_toggle_favorito(request):
    """Alternar favorito desde el catálogo (sesión Django + CSRF). Sin JWT."""
    uid = request.session.get(SESSION_USUARIO_ID)
    try:
        payload = json.loads(request.body.decode() or "{}")
        producto_id = int(payload.get("producto_id"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "message": "Solicitud inválida."}, status=400)
    en_favoritos = get_carrito_query_service().toggle_favorito(uid, producto_id)
    return JsonResponse(
        {
            "ok": True,
            "en_favoritos": en_favoritos,
            "message": "Favorito actualizado.",
        }
    )


@_admin_login_required
def perfil_view(request):
    """Mi Perfil (Administrador) - vuelve al layout original."""
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)

    mensajes_pendientes = MensajeDirecto.objects.exclude(
        estado=MensajeDirecto.Estado.RESPONDIDO
    ).count()
    notificaciones_no_leidas = Notificacion.objects.filter(
        usuario_id=uid, leida=False
    ).count()

    # Contar órdenes de compra (puede variar el path del módulo)
    ordenes_compra_count = 0
    try:
        from orden.infrastructure.models import OrdenCompra

        ordenes_compra_count = OrdenCompra.objects.count()
    except ImportError:
        try:
            from orden.models import OrdenCompra

            ordenes_compra_count = OrdenCompra.objects.count()
        except ImportError:
            pass

    ctx = {
        "usuario": usuario,
        "users_count": Usuario.objects.count(),
        "productos_count": Producto.objects.filter(activo=True).count(),
        "proveedores_count": Proveedor.objects.filter(activo=True).count(),
        "ordenes_compra_count": ordenes_compra_count,
        "reportes_disponibles": 3,
        "mensajes_pendientes": mensajes_pendientes,
        "notificaciones_no_leidas": notificaciones_no_leidas,
        "pedidos_procesados": Venta.objects.count(),
        "transacciones_procesadas": Pago.objects.count(),
    }
    return render(request, "frontend/admin/perfil_admin.html", ctx)


@_admin_login_required
def dashboard_view(request):
    """Dashboard Admin (métricas + gráficos)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)

    mensajes_pendientes = MensajeDirecto.objects.exclude(
        estado=MensajeDirecto.Estado.RESPONDIDO
    ).count()
    notificaciones_no_leidas = Notificacion.objects.filter(
        usuario_id=uid, leida=False
    ).count()

    # --- Dashboard Admin: métricas + gráficos (últimos 7 días) ---
    today = date.today()
    start_week = today - timedelta(days=6)
    start_month = today - timedelta(days=30)
    estados_validos = [Venta.Estado.ABIERTA, Venta.Estado.FACTURADA]

    ventas_totales = (
        Venta.objects.filter(estado__in=estados_validos).aggregate(total=Sum("total"))[
            "total"
        ]
        or 0
    )

    # "Pedidos nuevos" = ventas recientes (últimos 7 días), excl. anuladas.
    # El checkout crea Venta en estado FACTURADA (ver venta_transaction_adapter_impl);
    # filtrar solo ABIERTA dejaba el contador en 0 con pedidos reales.
    pedidos_nuevos_count = Venta.objects.filter(
        fecha_venta__gte=start_week,
        fecha_venta__lte=today,
    ).exclude(estado=Venta.Estado.ANULADA).count()

    clientes_registrados_count = Usuario.objects.filter(
        rol=Usuario.Rol.CLIENTE, activo=True
    ).count()

    productos_bajo_stock_count = Producto.objects.filter(
        activo=True, stock__gte=1, stock__lte=STOCK_BAJO_MAX
    ).count()

    # --- Sparklines KPI (ApexCharts) ---
    start_30 = today - timedelta(days=29)
    dias_30 = [start_30 + timedelta(days=i) for i in range(30)]
    ventas_30_map = {
        row["fecha_venta"]: (row["monto"] or 0)
        for row in Venta.objects.filter(
            fecha_venta__gte=start_30,
            fecha_venta__lte=today,
            estado__in=estados_validos,
        )
        .values("fecha_venta")
        .annotate(monto=Sum("total"))
        .order_by("fecha_venta")
    }
    sparkline_ventas_30d = [float(ventas_30_map.get(d, 0)) for d in dias_30]

    ganancia_line = ExpressionWrapper(
        F("cantidad") * (F("precio_unitario") - F("producto__costo_unitario")),
        output_field=DecimalField(max_digits=20, decimal_places=2),
    )
    total_ganancia = (
        DetalleVenta.objects.filter(venta__estado__in=estados_validos).aggregate(
            t=Sum(ganancia_line)
        )["t"]
        or 0
    )
    ganancia_30_rows = (
        DetalleVenta.objects.filter(
            venta__fecha_venta__gte=start_30,
            venta__fecha_venta__lte=today,
            venta__estado__in=estados_validos,
        )
        .values("venta__fecha_venta")
        .annotate(g=Sum(ganancia_line))
        .order_by("venta__fecha_venta")
    )
    ganancia_30_map = {
        r["venta__fecha_venta"]: float(r["g"] or 0) for r in ganancia_30_rows
    }
    sparkline_ganancias_30d = [ganancia_30_map.get(d, 0.0) for d in dias_30]

    now = timezone.now()
    start_24h = now - timedelta(hours=24)
    sparkline_pedidos_24h = [0] * 24
    for creado in Venta.objects.filter(creado_en__gte=start_24h).exclude(
        estado=Venta.Estado.ANULADA
    ).values_list("creado_en", flat=True):
        if creado is None:
            continue
        idx = int((creado - start_24h).total_seconds() // 3600)
        if 0 <= idx < 24:
            sparkline_pedidos_24h[idx] += 1

    # Ventas semanales: total por día
    dias = [start_week + timedelta(days=i) for i in range(7)]
    weekday_labels = {
        0: "Lun",
        1: "Mar",
        2: "Mié",
        3: "Jue",
        4: "Vie",
        5: "Sáb",
        6: "Dom",
    }
    ventas_semana_map = {
        row["fecha_venta"]: (row["monto"] or 0)
        for row in Venta.objects.filter(
            fecha_venta__gte=start_week,
            fecha_venta__lte=today,
            estado__in=estados_validos,
        )
        .values("fecha_venta")
        .annotate(monto=Sum("total"))
        .order_by("fecha_venta")
    }
    ventas_semana_labels = [weekday_labels[d.weekday()] for d in dias]
    ventas_semana_series = [float(ventas_semana_map.get(d, 0)) for d in dias]
    ventas_semana_rango = _dashboard_fmt_rango_es(start_week, today)

    # Ventas por mes (enero–abril 2026) para gráfico de barras.
    ventas_mes_anio = 2026
    ventas_mes_hasta = 4
    ventas_mes_labels = []
    ventas_mes_series = []
    for mes in range(1, ventas_mes_hasta + 1):
        ventas_mes_labels.append(["Ene", "Feb", "Mar", "Abr"][mes - 1])
        ultimo = monthrange(ventas_mes_anio, mes)[1]
        d_ini = date(ventas_mes_anio, mes, 1)
        d_fin = date(ventas_mes_anio, mes, ultimo)
        monto_mes = (
            Venta.objects.filter(
                fecha_venta__gte=d_ini,
                fecha_venta__lte=d_fin,
                estado__in=estados_validos,
            ).aggregate(t=Sum("total"))["t"]
            or 0
        )
        ventas_mes_series.append(float(monto_mes))

    clientes_dia_map = {}
    for row in (
        Usuario.objects.filter(rol=Usuario.Rol.CLIENTE)
        .filter(creado_en__date__gte=start_week, creado_en__date__lte=today)
        .annotate(d=TruncDay("creado_en"))
        .values("d")
        .annotate(c=Count("id"))
    ):
        dk = row.get("d")
        if dk is None:
            continue
        day_key = dk.date() if hasattr(dk, "date") else dk
        clientes_dia_map[day_key] = int(row["c"] or 0)
    sparkline_clientes_7d = [clientes_dia_map.get(d, 0) for d in dias]

    # Categorías más vendidas: sumar cantidades de DetalleVenta agrupadas por categoría del producto.
    detalles_validos = DetalleVenta.objects.filter(
        venta__fecha_venta__gte=start_month,
        venta__fecha_venta__lte=today,
        venta__estado__in=estados_validos,
    )
    celulares_qty = 0
    computadores_qty = 0
    accesorios_qty = 0
    for row in detalles_validos.values("producto__categoria").annotate(
        qty=Sum("cantidad")
    ):
        q = int(row["qty"] or 0)
        bucket = _dashboard_bucket_categoria(row.get("producto__categoria"))
        if bucket == "celulares":
            celulares_qty += q
        elif bucket == "computadores":
            computadores_qty += q
        else:
            accesorios_qty += q

    ctx = {
        "usuario": usuario,
        "mensajes_pendientes": mensajes_pendientes,
        "notificaciones_no_leidas": notificaciones_no_leidas,

        "ventas_totales_formatted": f"${ventas_totales:,.2f}",
        "total_ganancias_formatted": f"${total_ganancia:,.2f}",
        "pedidos_nuevos_count": pedidos_nuevos_count,
        "clientes_registrados_count": clientes_registrados_count,
        "productos_bajo_stock_count": productos_bajo_stock_count,

        "sparkline_ventas_30d_json": mark_safe(
            json.dumps(sparkline_ventas_30d, ensure_ascii=False)
        ),
        "sparkline_ganancias_30d_json": mark_safe(
            json.dumps(sparkline_ganancias_30d, ensure_ascii=False)
        ),
        "sparkline_pedidos_24h_json": mark_safe(
            json.dumps(sparkline_pedidos_24h, ensure_ascii=False)
        ),
        "sparkline_clientes_7d_json": mark_safe(
            json.dumps(sparkline_clientes_7d, ensure_ascii=False)
        ),

        "ventas_semana_labels_json": mark_safe(
            json.dumps(ventas_semana_labels, ensure_ascii=False)
        ),
        "ventas_semana_series_json": mark_safe(
            json.dumps(ventas_semana_series, ensure_ascii=False)
        ),
        "ventas_semana_rango": ventas_semana_rango,

        "ventas_mes_labels_json": mark_safe(
            json.dumps(ventas_mes_labels, ensure_ascii=False)
        ),
        "ventas_mes_series_json": mark_safe(
            json.dumps(ventas_mes_series, ensure_ascii=False)
        ),

        "categorias_donut_labels_json": mark_safe(
            json.dumps(["Celulares", "Computadores"], ensure_ascii=False)
        ),
        "categorias_donut_series_json": mark_safe(
            json.dumps(
                [int(celulares_qty), int(computadores_qty), int(accesorios_qty)],
                ensure_ascii=False,
            )
        ),
    }
    return render(request, "frontend/admin/dashboard.html", ctx)


@_admin_login_required
def perfil_admin(request):
    """Compatibilidad: si alguien llama a `perfil_admin`, muestra Mi Perfil."""
    return perfil_view(request)


@_admin_login_required
@require_http_methods(["GET", "POST"])
def admin_perfil_editar(request):
    """Edición de perfil solo para administrador (sidebar admin, no flujo cliente)."""
    usuario = _admin_usuario_sesion(request)

    def _ctx_form(
        *,
        nombres: str,
        apellidos: str,
        telefono: str,
        direccion: str,
        show_password_change: bool,
    ):
        return {
            "usuario": usuario,
            "form_nombres": nombres,
            "form_apellidos": apellidos,
            "form_telefono": telefono,
            "form_direccion": direccion,
            "show_password_change": show_password_change,
        }

    if request.method == "POST":
        nombres = (request.POST.get("nombres") or "").strip()
        apellidos = (request.POST.get("apellidos") or "").strip()
        telefono = (request.POST.get("telefono") or "").strip()
        direccion = (request.POST.get("direccion") or "").strip()
        current_password = request.POST.get("current_password") or ""
        new_password = (request.POST.get("new_password") or "").strip()
        confirm_password = (request.POST.get("confirm_password") or "").strip()

        errors: list[str] = []
        if not nombres or len(nombres) > 120:
            errors.append("Los nombres son obligatorios (máx. 120 caracteres).")
        if not apellidos or len(apellidos) > 120:
            errors.append("Los apellidos son obligatorios (máx. 120 caracteres).")
        if len(telefono) > 20:
            errors.append("El teléfono no puede superar 20 caracteres.")
        if len(direccion) > 2000:
            errors.append("La dirección es demasiado larga (máx. 2000 caracteres).")
        if not current_password:
            errors.append("Debes ingresar tu contraseña actual para guardar los cambios.")

        wants_pw_change = bool(new_password or confirm_password)
        if wants_pw_change:
            if not new_password or not confirm_password:
                errors.append("Completa el campo «Nueva contraseña» y «Confirmar nueva contraseña».")
            elif new_password != confirm_password:
                errors.append("La nueva contraseña y la confirmación no coinciden.")
            elif len(new_password) < 8:
                errors.append("La nueva contraseña debe tener al menos 8 caracteres.")

        if errors:
            for msg in errors:
                messages.error(request, msg)
            return render(
                request,
                "frontend/admin/perfil_editar.html",
                _ctx_form(
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                    direccion=direccion,
                    show_password_change=wants_pw_change,
                ),
            )

        if not credenciales_coinciden(current_password, usuario.contrasena_hash):
            messages.error(request, "La contraseña actual no es correcta.")
            return render(
                request,
                "frontend/admin/perfil_editar.html",
                _ctx_form(
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                    direccion=direccion,
                    show_password_change=wants_pw_change,
                ),
            )

        cambios: list[str] = []
        if usuario.nombres != nombres:
            cambios.append("nombres")
        if usuario.apellidos != apellidos:
            cambios.append("apellidos")
        if usuario.telefono != telefono:
            cambios.append("teléfono")
        if usuario.direccion != direccion:
            cambios.append("dirección")

        usuario.nombres = nombres
        usuario.apellidos = apellidos
        usuario.telefono = telefono
        usuario.direccion = direccion
        update_fields = ["nombres", "apellidos", "telefono", "direccion", "actualizado_en"]

        if wants_pw_change:
            usuario.contrasena_hash = make_password(new_password)
            update_fields.append("contrasena_hash")
            cambios.append("contraseña")

        usuario.save(update_fields=update_fields)

        if cambios:
            from mensajeria.services.notificaciones_admin import notificar_usuario_actualizado

            notificar_usuario_actualizado(
                usuario_id=usuario.id,
                correo=usuario.correo_electronico,
                cambios=cambios,
                origen="admin_perfil",
            )

        messages.success(request, "Perfil actualizado correctamente.")
        return redirect("web_admin_perfil")

    return render(
        request,
        "frontend/admin/perfil_editar.html",
        _ctx_form(
            nombres=usuario.nombres,
            apellidos=usuario.apellidos,
            telefono=usuario.telefono,
            direccion=usuario.direccion,
            show_password_change=False,
        ),
    )


@_admin_login_required
@require_http_methods(["GET", "POST"])
def admin_notificaciones(request):
    """Notificaciones del sistema para el administrador en sesión (solo lectura + marcar leídas)."""
    usuario = _admin_usuario_sesion(request)
    admin_uid = usuario.id

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()
        if accion == "marcar_leida":
            raw_id = request.POST.get("notificacion_id")
            if raw_id and str(raw_id).isdigit():
                n = Notificacion.objects.filter(
                    pk=int(raw_id), usuario_id=admin_uid
                ).update(leida=True)
                if n:
                    messages.success(request, "Notificación marcada como leída.")
                else:
                    messages.error(request, "No se encontró la notificación o no te pertenece.")
            else:
                messages.error(request, "Identificador de notificación no válido.")
        elif accion == "marcar_todas_leidas":
            n = Notificacion.objects.filter(usuario_id=admin_uid, leida=False).update(
                leida=True
            )
            messages.success(request, f"Se marcaron {n} notificación(es) como leídas.")
        else:
            messages.error(request, "Acción no reconocida.")
        return redirect("web_admin_notificaciones")

    leida_filtro = (request.GET.get("leida") or "").strip().lower()
    q = (request.GET.get("q") or "").strip()

    qs = (
        Notificacion.objects.filter(usuario_id=admin_uid)
        .select_related("usuario")
        .order_by("-fecha_creacion", "-id")
    )
    if leida_filtro == "si":
        qs = qs.filter(leida=True)
    elif leida_filtro == "no":
        qs = qs.filter(leida=False)
    if q:
        qs = qs.filter(Q(titulo__icontains=q) | Q(mensaje__icontains=q))

    notificaciones = list(qs[:500])
    total_recibidas = Notificacion.objects.filter(usuario_id=admin_uid).count()
    total_no_leidas = Notificacion.objects.filter(usuario_id=admin_uid, leida=False).count()

    return render(
        request,
        "frontend/admin/notificaciones.html",
        {
            "usuario": usuario,
            "notificaciones": notificaciones,
            "total_recibidas": total_recibidas,
            "total_no_leidas": total_no_leidas,
            "filtro_leida": leida_filtro,
            "filtro_q": q,
        },
    )


@_admin_login_required
@require_http_methods(["GET"])
def admin_notificaciones_poll(request):
    """JSON para actualizar el listado sin recargar (polling ~cada 12 s en la plantilla)."""
    usuario = _admin_usuario_sesion(request)
    admin_uid = usuario.id
    leida_filtro = (request.GET.get("leida") or "").strip().lower()
    q = (request.GET.get("q") or "").strip()

    qs = Notificacion.objects.filter(usuario_id=admin_uid).order_by(
        "-fecha_creacion", "-id"
    )
    if leida_filtro == "si":
        qs = qs.filter(leida=True)
    elif leida_filtro == "no":
        qs = qs.filter(leida=False)
    if q:
        qs = qs.filter(Q(titulo__icontains=q) | Q(mensaje__icontains=q))

    notificaciones = list(qs[:500])
    total_recibidas = Notificacion.objects.filter(usuario_id=admin_uid).count()
    total_no_leidas = Notificacion.objects.filter(
        usuario_id=admin_uid, leida=False
    ).count()

    items = [
        {
            "id": n.id,
            "titulo": n.titulo,
            "mensaje": n.mensaje,
            "tipo": n.tipo,
            "icono": n.icono,
            "leida": n.leida,
            "fecha_creacion": n.fecha_creacion.isoformat(),
        }
        for n in notificaciones
    ]
    return JsonResponse(
        {
            "total_recibidas": total_recibidas,
            "total_no_leidas": total_no_leidas,
            "notificaciones": items,
        }
    )


def _admin_usuario_sesion(request) -> Usuario:
    uid = request.session.get(SESSION_USUARIO_ID)
    return get_object_or_404(Usuario, pk=uid)


def _usuario_modal_dict(u: Usuario) -> dict:
    ventas_preview: list[dict] = []
    if u.rol == Usuario.Rol.CLIENTE:
        ventas_preview = [
            {
                "id": v.id,
                "fecha": v.fecha_venta.isoformat(),
                "total": str(v.total),
                "estado": v.estado,
            }
            for v in Venta.objects.filter(usuario=u).order_by("-fecha_venta")[:12]
        ]
    return {
        "id": u.id,
        "name": f"{u.nombres} {u.apellidos}".strip(),
        "firstName": u.nombres,
        "lastName": u.apellidos,
        "email": u.correo_electronico,
        "role": u.rol,
        "estado": u.activo,
        "documentType": u.tipo_documento,
        "documentNumber": u.numero_documento,
        "phone": u.telefono,
        "address": u.direccion,
        "ventas_preview": ventas_preview,
    }


def _producto_modal_dict(p: Producto) -> dict:
    precio = p.precio_venta if p.precio_venta is not None else p.costo_unitario
    return {
        "id": p.id,
        "codigo": p.codigo,
        "nombre": p.nombre,
        "stock": p.stock,
        "estado": p.activo,
        "imagen": p.imagen_url or "",
        "proveedor": p.proveedor.nombre if p.proveedor_id else "",
        "caracteristica": {
            "categoria": p.categoria,
            "marca": p.marca,
            "color": p.color or "",
            "descripcion": p.descripcion,
            "precioCompra": str(p.costo_unitario),
            "precioVenta": str(precio) if precio is not None else None,
        },
    }


def _proveedor_modal_dict(p: Proveedor) -> dict:
    return {
        "id": p.id,
        "identificacion": p.identificacion,
        "nombre": p.nombre,
        "telefono": p.telefono,
        "correo": p.correo_electronico,
        "empresa": p.empresa or "",
        "estado": p.activo,
    }


@_admin_login_required
def admin_usuarios(request):
    usuario = _admin_usuario_sesion(request)
    rol = (request.GET.get("rol") or "").strip().lower()
    busqueda = (request.GET.get("busqueda") or "").strip()

    qs = Usuario.objects.all().order_by("id")
    if rol in {Usuario.Rol.ADMIN, Usuario.Rol.CLIENTE, Usuario.Rol.EMPLEADO}:
        qs = qs.filter(rol=rol)
    if busqueda:
        qs = qs.filter(
            Q(nombres__icontains=busqueda)
            | Q(apellidos__icontains=busqueda)
            | Q(correo_electronico__icontains=busqueda)
            | Q(numero_documento__icontains=busqueda)
        )

    usuarios = list(qs)
    usuarios_json = json.dumps(
        [_usuario_modal_dict(u) for u in usuarios],
        ensure_ascii=False,
    )
    ctx = {
        "usuario": usuario,
        "usuarios": usuarios,
        "usuarios_json": mark_safe(usuarios_json),
        "rol": rol,
        "busqueda": busqueda,
        "total_usuarios": Usuario.objects.count(),
        "total_clientes": Usuario.objects.filter(rol=Usuario.Rol.CLIENTE).count(),
        "total_admin": Usuario.objects.filter(rol=Usuario.Rol.ADMIN).count(),
        "total_empleados": Usuario.objects.filter(rol=Usuario.Rol.EMPLEADO).count(),
    }
    return render(request, "frontend/admin/usuarios.html", ctx)


_NOMBRE_PERSONA_RE = re.compile(r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]{2,}$")
_EMAIL_ALTA_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _validar_nombre_persona(val: str) -> bool:
    val = (val or "").strip()
    if len(val) < 2:
        return False
    return bool(_NOMBRE_PERSONA_RE.match(val))


@_admin_login_required
@require_http_methods(["POST"])
def admin_usuario_crear(request):
    """Alta de administrador o empleado (misma regla que API + registro_usuario_service)."""
    admin = _admin_usuario_sesion(request)
    if admin.rol != Usuario.Rol.ADMIN:
        messages.error(request, "Solo el administrador puede crear usuarios desde esta pantalla.")
        return redirect("web_admin_usuarios")

    role = (request.POST.get("role") or "").strip().lower()
    if role not in (Usuario.Rol.ADMIN, Usuario.Rol.EMPLEADO):
        messages.error(request, "Debes seleccionar rol Administrador o Empleado.")
        return redirect("web_admin_usuarios")

    first_name = (request.POST.get("firstName") or "").strip()
    last_name = (request.POST.get("lastName") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    password = request.POST.get("password") or ""
    confirm = request.POST.get("confirmPassword") or ""
    phone = (request.POST.get("phone") or "").strip()
    doc_type = (request.POST.get("documentType") or "").strip()
    doc_num = (request.POST.get("documentNumber") or "").strip()
    address = (request.POST.get("address") or "").strip()

    if not _validar_nombre_persona(first_name):
        messages.error(
            request,
            "El primer nombre debe tener al menos 2 caracteres y solo letras.",
        )
        return redirect("web_admin_usuarios")
    if not _validar_nombre_persona(last_name):
        messages.error(
            request,
            "El apellido debe tener al menos 2 caracteres y solo letras.",
        )
        return redirect("web_admin_usuarios")
    if not _EMAIL_ALTA_RE.match(email):
        messages.error(request, "Ingresa un correo electrónico válido.")
        return redirect("web_admin_usuarios")
    if len(phone) != 10 or not phone.isdigit():
        messages.error(request, "El teléfono debe tener exactamente 10 dígitos.")
        return redirect("web_admin_usuarios")
    if not doc_type:
        messages.error(request, "Selecciona un tipo de documento.")
        return redirect("web_admin_usuarios")
    if len(address) < 8:
        messages.error(request, "La dirección debe tener al menos 8 caracteres.")
        return redirect("web_admin_usuarios")
    if password != confirm:
        messages.error(request, "Las contraseñas no coinciden.")
        return redirect("web_admin_usuarios")

    payload = {
        "email": email,
        "password": password,
        "firstName": first_name,
        "lastName": last_name,
        "documentType": doc_type,
        "documentNumber": doc_num,
        "phone": phone,
        "address": address,
        "role": role,
    }
    result = registrar_usuario_desde_payload(payload, admin_usuario=admin)
    if result.error:
        messages.error(request, result.error)
    else:
        messages.success(
            request,
            f"Usuario {result.usuario.correo_electronico} creado correctamente.",
        )
    return redirect("web_admin_usuarios")


@_admin_login_required
@require_http_methods(["POST"])
def admin_usuario_estado(request, usuario_id: int):
    _admin_usuario_sesion(request)
    activar = request.POST.get("activar") == "true"
    u = get_object_or_404(Usuario, pk=usuario_id)
    u.activo = activar
    u.save(update_fields=["activo", "actualizado_en"])
    messages.success(
        request,
        "Usuario activado correctamente." if activar else "Usuario desactivado correctamente.",
    )
    return redirect("web_admin_usuarios")


@_admin_login_required
def admin_inventario(request):
    usuario = _admin_usuario_sesion(request)
    categoria = (request.GET.get("categoria") or "").strip()
    busqueda = (request.GET.get("busqueda") or "").strip()
    nivel_stock = normalizar_nivel_stock_param(request.GET.get("nivel_stock") or "")

    qs = Producto.objects.all().select_related("proveedor").order_by("-creado_en", "-id")
    if categoria:
        qs = qs.filter(categoria__iexact=categoria)
    if busqueda:
        qs = qs.filter(Q(nombre__icontains=busqueda) | Q(codigo__icontains=busqueda))
    stock_q = q_filtro_listado_nivel_stock(nivel_stock)
    if stock_q is not None:
        qs = qs.filter(stock_q)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    productos = list(page_obj.object_list)

    get_params = request.GET.copy()
    get_params.pop("page", None)
    filtros_query_sin_page = get_params.urlencode()

    # Lista Python para |json_script — no usar json.dumps + json_script (doble codificación → string, no array).
    productos_data = [producto_modal_dict(p) for p in productos]

    total_productos = Producto.objects.count()
    productos_bajo_stock = Producto.objects.filter(
        activo=True, stock__gte=1, stock__lte=STOCK_BAJO_MAX
    ).count()
    productos_agotados = Producto.objects.filter(activo=True, stock=0).count()

    categorias_opts = sorted(
        set(Producto.objects.exclude(categoria="").values_list("categoria", flat=True).distinct())
        | _categorias_alta_permitidas(),
        key=str.lower,
    )

    counts_cat = {
        row["categoria"]: row["cantidad"]
        for row in Producto.objects.exclude(categoria="")
        .values("categoria")
        .annotate(cantidad=Count("id"))
    }
    extras_cat = set(
        ProductoCatalogoExtra.objects.filter(tipo=ProductoCatalogoExtra.Tipo.CATEGORIA).values_list(
            "nombre", flat=True
        )
    )
    categorias_info = [
        {"nombre": n, "cantidad": counts_cat.get(n, 0)}
        for n in sorted(set(counts_cat.keys()) | extras_cat, key=str.lower)
    ]

    counts_marca = {
        row["marca"]: row["cantidad"]
        for row in Producto.objects.exclude(marca="").values("marca").annotate(cantidad=Count("id"))
    }
    extras_marca = set(
        ProductoCatalogoExtra.objects.filter(tipo=ProductoCatalogoExtra.Tipo.MARCA).values_list("nombre", flat=True)
    )
    marcas_info = [
        {"nombre": n, "cantidad": counts_marca.get(n, 0)}
        for n in sorted(set(counts_marca.keys()) | extras_marca, key=str.lower)
    ]

    compras_recientes = []
    for c in Compra.objects.select_related("proveedor").order_by("-fecha_compra")[:15]:
        n_items = DetalleCompra.objects.filter(compra_id=c.id).count()
        compras_recientes.append(
            {
                "compra_id": c.id,
                "fecha_compra": c.fecha_compra,
                "total": c.total,
                "items": n_items,
            }
        )

    ventas_recientes = []
    for v in Venta.objects.select_related("usuario").order_by("-fecha_venta")[:15]:
        ventas_recientes.append(
            {
                "venta_id": v.id,
                "fecha_venta": v.fecha_venta,
                "usuario": v.usuario.correo_electronico if v.usuario_id else "",
            }
        )

    ctx = {
        "usuario": usuario,
        "page_obj": page_obj,
        "productos": productos,
        "filtros_query_sin_page": filtros_query_sin_page,
        "productos_data": productos_data,
        "categoria": categoria,
        "busqueda": busqueda,
        "nivel_stock": nivel_stock,
        "categorias_opts": categorias_opts,
        "total_productos": total_productos,
        "productos_bajo_stock": productos_bajo_stock,
        "productos_agotados": productos_agotados,
        "categorias_info": categorias_info,
        "marcas_info": marcas_info,
        "compras_recientes": compras_recientes,
        "ventas_recientes": ventas_recientes,
        "proveedores": Proveedor.objects.filter(activo=True).order_by("nombre"),
        "categorias_alta_list": sorted(_categorias_alta_permitidas(), key=str.lower),
        "marcas_alta_list": sorted(_marcas_alta_permitidas(), key=str.lower),
    }
    return render(request, "frontend/admin/inventario.html", ctx)


@_admin_login_required
@require_http_methods(["GET"])
def admin_inventario_plantilla_excel(request):
    """Descarga plantilla .xlsx para importación masiva de productos."""
    _admin_usuario_sesion(request)
    return respuesta_plantilla_excel()


@_admin_login_required
@require_http_methods(["POST"])
def admin_inventario_importar_excel(request):
    """Importa productos desde Excel; transacción atómica (todo o nada)."""
    _admin_usuario_sesion(request)
    archivo = request.FILES.get("archivo")
    if not archivo:
        messages.error(request, "Selecciona un archivo Excel (.xlsx).")
        return redirect("web_admin_inventario")
    nombre = (getattr(archivo, "name", "") or "").lower()
    if not nombre.endswith((".xlsx", ".xlsm")):
        messages.error(request, "El archivo debe ser Excel (.xlsx o .xlsm).")
        return redirect("web_admin_inventario")
    try:
        contenido = archivo.read()
        n = importar_productos_desde_bytes(contenido, get_producto_service)
        messages.success(request, f"¡Éxito! {n} productos cargados correctamente")
    except ErrorImportacionExcel as exc:
        messages.error(request, str(exc))
    except Exception as exc:
        logger.exception("Error inesperado en importación Excel")
        messages.error(request, f"Error al importar: {exc}")
    return redirect("web_admin_inventario")


def _decimal_desde_post(val: str | None) -> Decimal | None:
    if val is None:
        return None
    s = str(val).strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


_PRODUCTO_CATEGORIAS_ALTA_WEB = frozenset({"Celulares", "Portátiles"})
_PRODUCTO_MARCAS_ALTA_WEB = frozenset({"Apple", "Lenovo", "Motorola", "Xiaomi"})
_PRODUCTO_COLORES_ALTA_WEB = frozenset(
    {
        "Negro",
        "Blanco",
        "Gris",
        "Azul",
        "Rojo",
        "Dorado",
        "Plateado",
        "Verde",
        "Morado",
        "Rosa",
    }
)


def _normalizar_nombre_catalogo(s: str) -> str:
    return " ".join((s or "").strip().split())


def _categorias_alta_permitidas() -> set[str]:
    base = set(_PRODUCTO_CATEGORIAS_ALTA_WEB)
    extras = set(
        ProductoCatalogoExtra.objects.filter(tipo=ProductoCatalogoExtra.Tipo.CATEGORIA).values_list(
            "nombre", flat=True
        )
    )
    return base | extras


def _marcas_alta_permitidas() -> set[str]:
    base = set(_PRODUCTO_MARCAS_ALTA_WEB)
    extras = set(
        ProductoCatalogoExtra.objects.filter(tipo=ProductoCatalogoExtra.Tipo.MARCA).values_list("nombre", flat=True)
    )
    return base | extras


def _imagenes_adicionales_desde_post(request) -> list[str]:
    return [u.strip() for u in request.POST.getlist("imagenes_adicionales[]") if u.strip()]


def _validar_imagenes_adicionales_post(imagenes_adicionales: list[str]) -> str | None:
    for url in imagenes_adicionales:
        if len(url) > 500:
            return "Una URL de imagen adicional es demasiado larga."
        if not (url.startswith("http://") or url.startswith("https://")):
            return (
                "Las imágenes adicionales deben ser URLs que comiencen con http:// o https://"
            )
    return None


def _sincronizar_producto_imagenes_adicionales(producto_id: int, urls: list[str]) -> None:
    ProductoImagen.objects.filter(producto_id=producto_id).delete()
    for orden, url in enumerate(urls):
        ProductoImagen.objects.create(
            producto_id=producto_id,
            url=url,
            orden=orden + 1,
            activa=True,
        )


@_admin_login_required
@require_http_methods(["POST"])
def admin_producto_crear(request):
    """Alta de producto vía caso de uso (misma regla que API JSON)."""
    _admin_usuario_sesion(request)

    codigo = (request.POST.get("codigo") or "").strip()
    nombre = (request.POST.get("nombre") or "").strip()
    categoria = (request.POST.get("categoria") or "").strip()
    marca = (request.POST.get("marca") or "").strip()
    color = (request.POST.get("color") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    imagen_url = (request.POST.get("imagen_url") or "").strip()
    imagenes_adicionales = _imagenes_adicionales_desde_post(request)

    if not codigo or len(codigo) > 50:
        messages.error(request, "El código es obligatorio (máximo 50 caracteres).")
        return redirect("web_admin_inventario")
    if not nombre or len(nombre) > 120:
        messages.error(request, "El nombre es obligatorio (máximo 120 caracteres).")
        return redirect("web_admin_inventario")
    if categoria not in _categorias_alta_permitidas():
        messages.error(request, "Selecciona una categoría válida de la lista.")
        return redirect("web_admin_inventario")
    if marca not in _marcas_alta_permitidas():
        messages.error(request, "Selecciona una marca válida de la lista.")
        return redirect("web_admin_inventario")
    if color not in _PRODUCTO_COLORES_ALTA_WEB:
        messages.error(request, "Selecciona un color de la lista.")
        return redirect("web_admin_inventario")

    try:
        proveedor_id = int(request.POST.get("proveedor_id") or "0")
    except (TypeError, ValueError):
        messages.error(request, "Selecciona un proveedor válido.")
        return redirect("web_admin_inventario")

    if not Proveedor.objects.filter(pk=proveedor_id, activo=True).exists():
        messages.error(request, "El proveedor no existe o está inactivo.")
        return redirect("web_admin_inventario")

    try:
        stock = int(request.POST.get("stock") or "0")
        if stock < 0:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, "El stock debe ser un entero mayor o igual a 0.")
        return redirect("web_admin_inventario")

    costo = _decimal_desde_post(request.POST.get("costo_unitario"))
    if costo is None or costo < 0:
        messages.error(request, "El costo unitario debe ser un número mayor o igual a 0.")
        return redirect("web_admin_inventario")

    precio = _decimal_desde_post(request.POST.get("precio_venta"))
    if precio is None or precio <= 0:
        messages.error(request, "El precio de venta debe ser un número mayor que 0.")
        return redirect("web_admin_inventario")

    if precio <= costo:
        messages.error(request, "El precio de venta debe ser mayor que el costo unitario.")
        return redirect("web_admin_inventario")

    if imagen_url:
        if len(imagen_url) > 500:
            messages.error(request, "La URL de imagen es demasiado larga.")
            return redirect("web_admin_inventario")
        if not (imagen_url.startswith("http://") or imagen_url.startswith("https://")):
            messages.error(
                request,
                "La imagen debe ser una URL que comience con http:// o https://",
            )
            return redirect("web_admin_inventario")

    err_img_ad = _validar_imagenes_adicionales_post(imagenes_adicionales)
    if err_img_ad:
        messages.error(request, err_img_ad)
        return redirect("web_admin_inventario")

    entidad = ProductoEntidad(
        id=None,
        codigo=codigo,
        nombre=nombre,
        proveedor_id=proveedor_id,
        stock=stock,
        costo_unitario=costo,
        activo=True,
        imagen_url=imagen_url,
        categoria=categoria,
        marca=marca,
        color=color,
        descripcion=descripcion,
        precio_venta=precio,
    )
    service = get_producto_service()
    try:
        creado = service.crear(entidad)
        _sincronizar_producto_imagenes_adicionales(creado.id, imagenes_adicionales)
    except IntegrityError:
        messages.error(request, "Ya existe un producto con ese código.")
        return redirect("web_admin_inventario")
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))
        return redirect("web_admin_inventario")

    messages.success(request, f"Producto «{creado.nombre}» creado correctamente.")
    return redirect("web_admin_inventario")


@_admin_login_required
@require_http_methods(["POST"])
def admin_producto_estado(request, producto_id: int):
    _admin_usuario_sesion(request)
    activar = request.POST.get("activar") == "true"
    p = get_object_or_404(Producto, pk=producto_id)
    estado_anterior = p.activo
    p.activo = activar
    p.save(update_fields=["activo", "actualizado_en"])
    if estado_anterior != activar:
        from mensajeria.services.notificaciones_admin import notificar_producto_actualizado

        notificar_producto_actualizado(
            producto_id=p.id,
            nombre=p.nombre,
            cambios=["activado" if activar else "desactivado"],
        )
    messages.success(
        request,
        "Producto activado correctamente." if activar else "Producto desactivado correctamente.",
    )
    return redirect("web_admin_inventario")


@_admin_login_required
@require_http_methods(["POST"])
def admin_producto_editar(request, producto_id: int):
    """Actualiza un producto; el código no se modifica. Requiere contraseña del admin en sesión."""
    admin = _admin_usuario_sesion(request)
    pwd = (request.POST.get("confirmacion_contrasena") or "").strip()
    if not pwd or not credenciales_coinciden(pwd, admin.contrasena_hash):
        messages.error(request, "La contraseña de confirmación no es correcta.")
        return redirect("web_admin_inventario")

    p = get_object_or_404(Producto, pk=producto_id)

    nombre = (request.POST.get("nombre") or "").strip()
    categoria = (request.POST.get("categoria") or "").strip()
    marca = (request.POST.get("marca") or "").strip()
    color = (request.POST.get("color") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    imagen_url = (request.POST.get("imagen_url") or "").strip()
    imagenes_adicionales = _imagenes_adicionales_desde_post(request)

    if not nombre or len(nombre) > 120:
        messages.error(request, "El nombre es obligatorio (máximo 120 caracteres).")
        return redirect("web_admin_inventario")

    cat_permitidas = _categorias_alta_permitidas()
    if categoria not in cat_permitidas and categoria != (p.categoria or "").strip():
        messages.error(request, "Selecciona una categoría válida de la lista.")
        return redirect("web_admin_inventario")

    mar_permitidas = _marcas_alta_permitidas()
    if marca not in mar_permitidas and marca != (p.marca or "").strip():
        messages.error(request, "Selecciona una marca válida de la lista.")
        return redirect("web_admin_inventario")

    if color not in _PRODUCTO_COLORES_ALTA_WEB and color != (p.color or "").strip():
        messages.error(request, "Selecciona un color de la lista.")
        return redirect("web_admin_inventario")

    # El stock no se ajusta desde este formulario (solo lectura en UI).
    stock = int(p.stock)

    costo = _decimal_desde_post(request.POST.get("costo_unitario"))
    if costo is None or costo < 0:
        messages.error(request, "El costo unitario debe ser un número mayor o igual a 0.")
        return redirect("web_admin_inventario")

    precio = _decimal_desde_post(request.POST.get("precio_venta"))
    if precio is None or precio <= 0:
        messages.error(request, "El precio de venta debe ser un número mayor que 0.")
        return redirect("web_admin_inventario")

    if precio <= costo:
        messages.error(request, "El precio de venta debe ser mayor que el costo unitario.")
        return redirect("web_admin_inventario")

    if imagen_url:
        if len(imagen_url) > 500:
            messages.error(request, "La URL de imagen es demasiado larga.")
            return redirect("web_admin_inventario")
        if not (imagen_url.startswith("http://") or imagen_url.startswith("https://")):
            messages.error(
                request,
                "La imagen debe ser una URL que comience con http:// o https://",
            )
            return redirect("web_admin_inventario")

    err_img_ad = _validar_imagenes_adicionales_post(imagenes_adicionales)
    if err_img_ad:
        messages.error(request, err_img_ad)
        return redirect("web_admin_inventario")

    if len(descripcion) > 4000:
        messages.error(request, "La descripción es demasiado larga (máx. 4000 caracteres).")
        return redirect("web_admin_inventario")

    cambios: list[str] = []
    if p.nombre != nombre:
        cambios.append("nombre")
    if (p.categoria or "") != categoria:
        cambios.append("categoría")
    if (p.marca or "") != marca:
        cambios.append("marca")
    if (p.color or "") != color:
        cambios.append("color")
    if (p.descripcion or "") != descripcion:
        cambios.append("descripción")
    if (p.imagen_url or "").strip() != imagen_url:
        cambios.append("imagen")
    if p.costo_unitario != costo:
        cambios.append("costo")
    if p.precio_venta != precio:
        cambios.append("precio venta")

    entidad = ProductoEntidad(
        id=p.id,
        codigo=p.codigo,
        nombre=nombre,
        proveedor_id=p.proveedor_id,
        stock=stock,
        costo_unitario=costo,
        activo=p.activo,
        imagen_url=imagen_url,
        categoria=categoria,
        marca=marca,
        color=color,
        descripcion=descripcion,
        precio_venta=precio,
    )
    service = get_producto_service()
    try:
        actualizado = service.actualizar(entidad)
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))
        return redirect("web_admin_inventario")

    if actualizado is None:
        messages.error(request, "No se pudo actualizar el producto.")
        return redirect("web_admin_inventario")

    _sincronizar_producto_imagenes_adicionales(p.id, imagenes_adicionales)

    if cambios:
        from mensajeria.services.notificaciones_admin import notificar_producto_actualizado

        notificar_producto_actualizado(
            producto_id=p.id,
            nombre=nombre,
            cambios=cambios,
        )

    messages.success(request, f"Producto «{nombre}» actualizado correctamente.")
    return redirect("web_admin_inventario")


def _redirect_inventario_tab_marcas():
    return redirect(reverse("web_admin_inventario") + "?tab=marcas")


@_admin_login_required
@require_http_methods(["POST"])
def admin_catalogo_categoria_agregar(request):
    _admin_usuario_sesion(request)
    nombre = _normalizar_nombre_catalogo(request.POST.get("nombre") or "")
    if len(nombre) < 2:
        messages.error(request, "El nombre de categoría debe tener al menos 2 caracteres.")
        return _redirect_inventario_tab_marcas()
    if len(nombre) > 120:
        messages.error(request, "El nombre es demasiado largo.")
        return _redirect_inventario_tab_marcas()
    if nombre in _PRODUCTO_CATEGORIAS_ALTA_WEB:
        messages.info(request, "Esa categoría ya está disponible en el sistema.")
        return _redirect_inventario_tab_marcas()
    if ProductoCatalogoExtra.objects.filter(
        tipo=ProductoCatalogoExtra.Tipo.CATEGORIA, nombre__iexact=nombre
    ).exists():
        messages.warning(request, "Esa categoría ya fue registrada.")
        return _redirect_inventario_tab_marcas()
    try:
        ProductoCatalogoExtra.objects.create(
            tipo=ProductoCatalogoExtra.Tipo.CATEGORIA, nombre=nombre
        )
    except IntegrityError:
        messages.warning(request, "Esa categoría ya existe.")
        return _redirect_inventario_tab_marcas()
    messages.success(request, f"Categoría «{nombre}» agregada. Ya puedes usarla al crear productos.")
    return _redirect_inventario_tab_marcas()


@_admin_login_required
@require_http_methods(["POST"])
def admin_catalogo_marca_agregar(request):
    _admin_usuario_sesion(request)
    nombre = _normalizar_nombre_catalogo(request.POST.get("nombre") or "")
    if len(nombre) < 2:
        messages.error(request, "El nombre de marca debe tener al menos 2 caracteres.")
        return _redirect_inventario_tab_marcas()
    if len(nombre) > 120:
        messages.error(request, "El nombre es demasiado largo.")
        return _redirect_inventario_tab_marcas()
    if nombre in _PRODUCTO_MARCAS_ALTA_WEB:
        messages.info(request, "Esa marca ya está disponible en el sistema.")
        return _redirect_inventario_tab_marcas()
    if ProductoCatalogoExtra.objects.filter(
        tipo=ProductoCatalogoExtra.Tipo.MARCA, nombre__iexact=nombre
    ).exists():
        messages.warning(request, "Esa marca ya fue registrada.")
        return _redirect_inventario_tab_marcas()
    try:
        ProductoCatalogoExtra.objects.create(tipo=ProductoCatalogoExtra.Tipo.MARCA, nombre=nombre)
    except IntegrityError:
        messages.warning(request, "Esa marca ya existe.")
        return _redirect_inventario_tab_marcas()
    messages.success(request, f"Marca «{nombre}» agregada. Ya puedes usarla al crear productos.")
    return _redirect_inventario_tab_marcas()


_TELEFONO_PROV_RE = re.compile(r"^[\d\s+\-().]{7,20}$")


@_admin_login_required
def admin_proveedores(request):
    usuario = _admin_usuario_sesion(request)
    busqueda = (request.GET.get("busqueda") or "").strip()
    qs = Proveedor.objects.all().order_by("id")
    if busqueda:
        qs = qs.filter(
            Q(nombre__icontains=busqueda)
            | Q(identificacion__icontains=busqueda)
            | Q(correo_electronico__icontains=busqueda)
            | Q(empresa__icontains=busqueda)
        )
    proveedores = list(qs)
    proveedores_json = json.dumps(
        [_proveedor_modal_dict(p) for p in proveedores],
        ensure_ascii=False,
    )
    ctx = {
        "usuario": usuario,
        "proveedores": proveedores,
        "proveedores_json": mark_safe(proveedores_json),
        "busqueda": busqueda,
        "total_proveedores": Proveedor.objects.count(),
        "total_activos": Proveedor.objects.filter(activo=True).count(),
        "total_inactivos": Proveedor.objects.filter(activo=False).count(),
    }
    return render(request, "frontend/admin/proveedores.html", ctx)


@_admin_login_required
@require_http_methods(["POST"])
def admin_proveedor_crear(request):
    _admin_usuario_sesion(request)

    identificacion = (request.POST.get("identificacion") or "").strip()
    nombre = (request.POST.get("nombre") or "").strip()
    telefono = (request.POST.get("telefono") or "").strip()
    correo = (request.POST.get("correo_electronico") or "").strip().lower()
    empresa = (request.POST.get("empresa") or "").strip()

    if not identificacion or len(identificacion) > 50:
        messages.error(request, "La identificación es obligatoria (máximo 50 caracteres).")
        return redirect("web_admin_proveedores")
    if not nombre or len(nombre) > 120:
        messages.error(request, "El nombre es obligatorio (máximo 120 caracteres).")
        return redirect("web_admin_proveedores")
    digitos_tel = sum(1 for c in telefono if c.isdigit())
    if (
        not telefono
        or len(telefono) > 20
        or not _TELEFONO_PROV_RE.match(telefono)
        or digitos_tel < 7
    ):
        messages.error(
            request,
            "El teléfono es obligatorio: al menos 7 dígitos, máximo 20 caracteres totales "
            "(puedes usar espacios, +, - o paréntesis).",
        )
        return redirect("web_admin_proveedores")
    if not _EMAIL_ALTA_RE.match(correo):
        messages.error(request, "Ingresa un correo electrónico válido.")
        return redirect("web_admin_proveedores")
    if len(empresa) > 150:
        messages.error(request, "El nombre de empresa es demasiado largo (máx. 150).")
        return redirect("web_admin_proveedores")

    entidad = ProveedorEntidad(
        id=None,
        identificacion=identificacion,
        nombre=nombre,
        telefono=telefono,
        correo_electronico=correo,
        empresa=empresa,
        activo=True,
    )
    service = get_proveedor_service()
    try:
        creado = service.crear(entidad)
    except IntegrityError:
        messages.error(
            request,
            "Ya existe un proveedor con esa identificación o ese correo electrónico.",
        )
        return redirect("web_admin_proveedores")
    except Exception as exc:  # noqa: BLE001
        messages.error(request, str(exc))
        return redirect("web_admin_proveedores")

    messages.success(request, f"Proveedor «{creado.nombre}» creado correctamente.")
    return redirect("web_admin_proveedores")


@_admin_login_required
@require_http_methods(["POST"])
def admin_proveedor_estado(request, proveedor_id: int):
    _admin_usuario_sesion(request)
    activar = request.POST.get("activar") == "true"
    p = get_object_or_404(Proveedor, pk=proveedor_id)
    p.activo = activar
    p.save(update_fields=["activo", "actualizado_en"])
    messages.success(
        request,
        "Proveedor activado correctamente." if activar else "Proveedor desactivado correctamente.",
    )
    return redirect("web_admin_proveedores")


@_admin_login_required
def admin_pagos(request):
    """Listado de pagos con filtros (equivalente a /admin/pagos en Spring)."""
    usuario = _admin_usuario_sesion(request)
    estado = (request.GET.get("estado") or "").strip()
    fecha_desde = _parse_date_param(request.GET.get("fechaDesde"))
    fecha_hasta = _parse_date_param(request.GET.get("fechaHasta"))
    busqueda = (request.GET.get("busqueda") or "").strip()
    orden = (request.GET.get("orden") or "reciente").strip().lower()

    todos = Pago.objects.all()
    total_pagos = todos.count()
    agg = todos.aggregate(s=Sum("monto"))
    total_monto = agg["s"] or Decimal("0")
    pagos_confirmados = todos.filter(estado_pago=Pago.EstadoPago.APROBADO).count()

    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    agg_mes = todos.filter(fecha_pago__gte=inicio_mes, fecha_pago__lte=hoy).aggregate(
        s=Sum("monto")
    )
    monto_este_mes = agg_mes["s"] or Decimal("0")

    qs = Pago.objects.prefetch_related(
        Prefetch(
            "medios_pago",
            queryset=MedioPago.objects.select_related("detalle_venta__venta__usuario"),
        )
    ).order_by("-fecha_pago", "-id")
    qs = _filtrar_queryset_pagos_por_estado_get(qs, estado or None)
    if fecha_desde:
        qs = qs.filter(fecha_pago__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_pago__lte=fecha_hasta)

    rows = []
    for pago in qs:
        venta, cliente = _venta_cliente_desde_pago(pago)
        rows.append(
            {
                "pago": pago,
                "venta": venta,
                "cliente": cliente,
                "badge": _badge_clase_estado_pago(pago.estado_pago),
            }
        )

    if busqueda:
        q_lower = busqueda.lower()

        def _match(r: dict) -> bool:
            p = r["pago"]
            if p.numero_factura and q_lower in p.numero_factura.lower():
                return True
            c = r["cliente"]
            if c:
                nombre = f"{c.nombres} {c.apellidos}".strip().lower()
                if q_lower in nombre or q_lower in (c.correo_electronico or "").lower():
                    return True
            return False

        rows = [r for r in rows if _match(r)]

    rows = [r for r in rows if r["venta"] is not None]

    if orden == "antiguo":
        rows.sort(key=lambda r: (r["pago"].fecha_pago, r["pago"].id))
    else:
        rows.sort(key=lambda r: (r["pago"].fecha_pago, r["pago"].id), reverse=True)

    ctx = {
        "usuario": usuario,
        "rows": rows,
        "estado": estado,
        "fecha_desde": request.GET.get("fechaDesde") or "",
        "fecha_hasta": request.GET.get("fechaHasta") or "",
        "busqueda": busqueda,
        "orden": orden,
        "total_pagos": total_pagos,
        "total_monto": total_monto,
        "pagos_confirmados": pagos_confirmados,
        "monto_este_mes": monto_este_mes,
    }
    return render(request, "frontend/admin/pagos.html", ctx)


@_admin_login_required
def admin_pago_detalle(request, pago_id: int):
    usuario = _admin_usuario_sesion(request)
    pago = get_object_or_404(
        Pago.objects.prefetch_related(
            Prefetch(
                "medios_pago",
                queryset=MedioPago.objects.select_related(
                    "detalle_venta__venta__usuario",
                    "detalle_venta__venta__empleado",
                    "detalle_venta__venta__administrador",
                ),
            )
        ),
        pk=pago_id,
    )
    venta, cliente = _venta_cliente_desde_pago(pago)
    if venta is None:
        messages.error(request, "No se encontró la venta asociada a este pago.")
        return redirect("web_admin_pagos")
    lineas = [
        {
            "nombre": d.producto.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "subtotal": d.precio_unitario * d.cantidad,
        }
        for d in venta.detalles.select_related("producto").all()
    ]
    badge = _badge_clase_estado_pago(pago.estado_pago)
    medios_pago_labels = _lista_metodos_pago_display(pago)
    if venta.empleado_id:
        venta_origen_label = f"Empleado: {venta.empleado.nombres} {venta.empleado.apellidos}".strip()
    elif venta.administrador_id:
        venta_origen_label = (
            f"Administrador: {venta.administrador.nombres} {venta.administrador.apellidos}".strip()
        )
    elif getattr(venta, "tipo_venta", None) == "fisica":
        venta_origen_label = "Punto de venta"
    else:
        venta_origen_label = "Cliente (compra en tienda online)"

    return render(
        request,
        "frontend/admin/pago_detalle.html",
        {
            "usuario": usuario,
            "pago": pago,
            "venta": venta,
            "cliente": cliente,
            "lineas": lineas,
            "badge": badge,
            "medios_pago_labels": medios_pago_labels,
            "fecha_pago_es": _fecha_larga_es(pago.fecha_pago),
            "fecha_factura_es": _fecha_larga_es(pago.fecha_factura),
            "tipo_venta_display": venta.get_tipo_venta_display(),
            "venta_origen_label": venta_origen_label,
        },
    )


@_admin_login_required
def admin_pago_factura(request, pago_id: int):
    usuario = _admin_usuario_sesion(request)
    pago = get_object_or_404(
        Pago.objects.prefetch_related(
            Prefetch(
                "medios_pago",
                queryset=MedioPago.objects.select_related("detalle_venta__venta__usuario"),
            )
        ),
        pk=pago_id,
    )
    venta, cliente = _venta_cliente_desde_pago(pago)
    if venta is None:
        messages.error(request, "No se encontró la venta para generar la factura.")
        return redirect("web_admin_pagos")
    lineas = [
        {
            "nombre": d.producto.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "subtotal": d.precio_unitario * d.cantidad,
        }
        for d in venta.detalles.select_related("producto").all()
    ]
    return render(
        request,
        "frontend/admin/factura_pago.html",
        {
            "usuario": usuario,
            "pago": pago,
            "venta": venta,
            "cliente": cliente,
            "lineas": lineas,
        },
    )


@_admin_login_required
def admin_pedidos(request):
    """Listado de ventas / pedidos (panel admin, alineado a gestión de pedidos)."""
    usuario = _admin_usuario_sesion(request)
    busqueda = (request.GET.get("busqueda") or "").strip()
    usuario_id = (request.GET.get("usuarioId") or "").strip()
    fecha_desde = (request.GET.get("fechaDesde") or "").strip()
    fecha_hasta = (request.GET.get("fechaHasta") or "").strip()
    producto = (request.GET.get("producto") or "").strip()
    qs = Venta.objects.select_related("usuario").order_by("-fecha_venta", "-id")
    if usuario_id.isdigit():
        qs = qs.filter(usuario_id=int(usuario_id))
    if fecha_desde:
        try:
            f_desde = datetime.strptime(fecha_desde, "%Y-%m-%d").date()
            qs = qs.filter(fecha_venta__gte=f_desde)
        except ValueError:
            fecha_desde = ""
    if fecha_hasta:
        try:
            f_hasta = datetime.strptime(fecha_hasta, "%Y-%m-%d").date()
            qs = qs.filter(fecha_venta__lte=f_hasta)
        except ValueError:
            fecha_hasta = ""
    if producto:
        qs = qs.filter(detalles__producto__nombre__icontains=producto).distinct()
    if busqueda:
        if busqueda.isdigit():
            qs = qs.filter(id=int(busqueda))
        else:
            qs = qs.filter(
                Q(usuario__nombres__icontains=busqueda)
                | Q(usuario__apellidos__icontains=busqueda)
                | Q(usuario__correo_electronico__icontains=busqueda)
            )
    ventas = list(qs[:800])
    usuarios_filtro = list(
        Usuario.objects.filter(ventas__isnull=False)
        .distinct()
        .order_by("nombres", "apellidos")
        .values("id", "nombres", "apellidos", "correo_electronico")
    )
    hoy = timezone.localdate()
    total_pedidos = Venta.objects.count()
    agg_monto = Venta.objects.aggregate(s=Sum("total"))
    total_ventas_monto = agg_monto["s"] if agg_monto["s"] is not None else Decimal("0")
    pedidos_este_mes = Venta.objects.filter(
        fecha_venta__year=hoy.year,
        fecha_venta__month=hoy.month,
    ).count()
    return render(
        request,
        "frontend/admin/pedidos.html",
        {
            "usuario": usuario,
            "ventas": ventas,
            "busqueda": busqueda,
            "usuarios_filtro": usuarios_filtro,
            "usuario_id": usuario_id,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "producto": producto,
            "total_pedidos": total_pedidos,
            "total_ventas_monto": total_ventas_monto,
            "pedidos_este_mes": pedidos_este_mes,
        },
    )


@_admin_login_required
def admin_pedido_detalle(request, venta_id: int):
    usuario = _admin_usuario_sesion(request)
    venta = get_object_or_404(Venta.objects.select_related("usuario"), pk=venta_id)
    detalles = venta.detalles.select_related("producto").all()
    lineas = [
        {
            "nombre": d.producto.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "subtotal": d.precio_unitario * d.cantidad,
        }
        for d in detalles
    ]
    envio = (
        Envio.objects.filter(venta_id=venta.id, activo=True)
        .select_related("transportadora")
        .order_by("-id")
        .first()
    )
    pago = Pago.objects.filter(medios_pago__detalle_venta__venta_id=venta.id).distinct().first()
    medio_pago = None
    if pago:
        medio_pago = (
            MedioPago.objects.filter(pago=pago, detalle_venta__venta_id=venta.id)
            .order_by("id")
            .first()
        )
    medio_pago_etiqueta = _etiqueta_medio_pago_mostrar(medio_pago) if medio_pago else ""
    return render(
        request,
        "frontend/admin/pedido_detalle.html",
        {
            "usuario": usuario,
            "venta": venta,
            "cliente": venta.usuario,
            "lineas": lineas,
            "envio": envio,
            "pago": pago,
            "medio_pago": medio_pago,
            "medio_pago_etiqueta": medio_pago_etiqueta,
        },
    )


def _reporte_filtrar_productos(
    *, categoria: str = "", marca: str = "", precio_min: Decimal | None = None, precio_max: Decimal | None = None
):
    qs = Producto.objects.select_related("proveedor").order_by("id")
    if categoria:
        qs = qs.filter(categoria__iexact=categoria)
    if marca:
        qs = qs.filter(marca__iexact=marca)
    if precio_min is not None:
        qs = qs.filter(precio_venta__gte=precio_min)
    if precio_max is not None:
        qs = qs.filter(precio_venta__lte=precio_max)
    return qs


def _reporte_filtrar_usuarios(*, rol: str = "", busqueda: str = ""):
    qs = Usuario.objects.all().order_by("id")
    if rol in {Usuario.Rol.ADMIN, Usuario.Rol.CLIENTE, Usuario.Rol.EMPLEADO}:
        qs = qs.filter(rol=rol)
    if busqueda:
        qs = qs.filter(
            Q(nombres__icontains=busqueda)
            | Q(apellidos__icontains=busqueda)
            | Q(correo_electronico__icontains=busqueda)
            | Q(numero_documento__icontains=busqueda)
        )
    return qs


def _reporte_filtrar_ventas(*, estado: str = "", fecha_desde: str = "", fecha_hasta: str = ""):
    qs = Venta.objects.select_related("usuario").order_by("-fecha_venta", "-id")
    if estado in {Venta.Estado.ABIERTA, Venta.Estado.FACTURADA, Venta.Estado.ANULADA}:
        qs = qs.filter(estado=estado)

    fd = _parse_date_param(fecha_desde) if fecha_desde else None
    fh = _parse_date_param(fecha_hasta) if fecha_hasta else None
    if fd:
        qs = qs.filter(fecha_venta__gte=fd)
    if fh:
        qs = qs.filter(fecha_venta__lte=fh)
    return qs


def _reporte_rango_default(request) -> tuple[str, str, date | None, date | None]:
    """
    Rango de fechas para reportes.
    - Si el usuario no envía rango, se usa por defecto: inicio del mes actual → hoy.
    - Devuelve: (raw_desde, raw_hasta, date_desde, date_hasta)
    """
    raw_desde = (request.GET.get("fechaDesde") or "").strip()
    raw_hasta = (request.GET.get("fechaHasta") or "").strip()
    fd = _parse_date_param(raw_desde) if raw_desde else None
    fh = _parse_date_param(raw_hasta) if raw_hasta else None
    if fd is None or fh is None:
        hoy = timezone.localdate()
        fd = hoy.replace(day=1)
        fh = hoy
        raw_desde = fd.isoformat()
        raw_hasta = fh.isoformat()
    return raw_desde, raw_hasta, fd, fh


def _reporte_rango_label(raw_desde: str, raw_hasta: str) -> str:
    return f"Rango: {raw_desde} → {raw_hasta}"


def _reporte_add_months(d: date, delta: int) -> date:
    """Suma meses a una fecha (día recortado al último día del mes destino)."""
    m = d.month - 1 + delta
    y = d.year + m // 12
    m = m % 12 + 1
    last = monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


# Umbral explícito para alerta de stock en reporte BI (independiente de STOCK_BAJO_MAX del catálogo)
_REPORTE_STOCK_ALERTA_CRITICO = 3

_MESES_CORTO = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")


def _reporte_norm_kpi_item(item) -> tuple[str, str, str]:
    """Normaliza KPI para PDF/preview: (etiqueta, valor, clave de icono)."""
    if isinstance(item, dict):
        return (
            str(item.get("label") or ""),
            str(item.get("valor") or ""),
            str(item.get("icon") or "dot"),
        )
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        ic = str(item[2]) if len(item) >= 3 else "dot"
        return (str(item[0]), str(item[1]), ic)
    return ("", "", "dot")


def _cop(valor: Decimal | int | float | None) -> str:
    """COP para PDF: miles con punto (formato colombiano habitual), sin decimales."""
    if valor is None:
        return "$0"
    try:
        d = Decimal(str(valor))
        n = int(d.quantize(Decimal("1")))
        s = f"{abs(n):,}".replace(",", ".")
        if n < 0:
            return f"-${s}"
        return f"${s}"
    except Exception:  # noqa: BLE001
        return f"${valor}"


def _format_cop_axis_short(val: float) -> str:
    """Eje Y / etiquetas compactas en gráficas (ej. $2.4M, $850k)."""
    v = max(0.0, float(val))
    if v >= 1_000_000_000:
        return f"${v / 1_000_000_000:.1f}B"
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1_000:.0f}k"
    return f"${int(round(v))}"


def _cop_decimales(valor: Decimal | int | float | None) -> str:
    """COP con miles en punto y dos decimales tras coma (ej. $10.500.000,00)."""
    if valor is None:
        return "$0,00"
    try:
        d = Decimal(str(valor)).quantize(Decimal("0.01"))
        sign = "-" if d < 0 else ""
        d = abs(d)
        intpart = int(d)
        frac_part = d - Decimal(intpart)
        frac = int((frac_part * 100).quantize(Decimal("1")))
        if frac >= 100:
            intpart += 1
            frac = 0
        s_int = f"{intpart:,}".replace(",", ".")
        return f"{sign}${s_int},{frac:02d}"
    except Exception:  # noqa: BLE001
        return f"${valor}"


_MARCA_ICON_NEEDLES = (
    ("apple", "apple"),
    ("iphone", "apple"),
    ("samsung", "samsung"),
    ("xiaomi", "xiaomi"),
    ("huawei", "huawei"),
    ("sony", "sony"),
    ("lg", "lg"),
    ("motorola", "motorola"),
    ("google", "google"),
    ("pixel", "google"),
    ("oneplus", "oneplus"),
    ("oppo", "oppo"),
    ("vivo", "vivo"),
    ("realme", "realme"),
    ("asus", "asus"),
    ("acer", "acer"),
    ("hp", "hp"),
    ("lenovo", "lenovo"),
    ("dell", "dell"),
    ("msi", "msi"),
)


def _reporte_marca_icon_abs_path(marca: str) -> str | None:
    """Ruta absoluta a PNG en static/frontend/marcas/{nombre}.png si existe."""
    try:
        from django.contrib.staticfiles import finders
    except Exception:  # noqa: BLE001
        return None
    m = (marca or "").lower()
    for needle, fname in _MARCA_ICON_NEEDLES:
        if needle in m:
            p = finders.find(f"frontend/marcas/{fname}.png")
            return str(p) if p else None
    return None


def _hex_to_rgb01(h: str) -> tuple[float, float, float]:
    h = (h or "#000000").lstrip("#")
    if len(h) != 6:
        return (0.2, 0.2, 0.35)
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _lerp_color_hex(hex_a: str, hex_b: str, t: float):
    """Interpola entre dos colores hex (ReportLab Color). Usado en degradados morado→azul."""
    from reportlab.lib import colors as rl_colors

    r1, g1, b1 = _hex_to_rgb01(hex_a)
    r2, g2, b2 = _hex_to_rgb01(hex_b)
    u = max(0.0, min(1.0, float(t)))
    return rl_colors.Color(r1 * (1 - u) + r2 * u, g1 * (1 - u) + g2 * u, b1 * (1 - u) + b2 * u)


def _reporte_poly_points_flat(pts: list[tuple[float, float]]) -> list[float]:
    o: list[float] = []
    for x, y in pts:
        o.extend((float(x), float(y)))
    return o


try:
    from reportlab.platypus import Flowable as _ReportLabFlowable
except Exception:  # noqa: BLE001
    _ReportLabFlowable = object


class _ReporteRadialTop5Flowable(_ReportLabFlowable):
    """Anillos concéntricos tipo gauge (referencia radial BI): arco proporcional al volumen."""

    def __init__(self, items: list[dict], width: float = 460, height: float = 212):
        if _ReportLabFlowable is not object:
            _ReportLabFlowable.__init__(self)
        self._items = items
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):  # noqa: ANN001, N802
        return self.width, self.height

    def draw(self):
        c = self.canv
        cx = 118.0
        cy = self.height * 0.52
        max_r = 78.0
        dr = 13.5
        sweep_max = 310.0

        c.saveState()
        c.setLineCap(1)

        n = len(self._items)
        for i in range(n):
            it = self._items[i]
            r = max_r - i * dr
            frac = float(it.get("arc_frac") or 0)
            frac = max(0.06, min(1.0, frac))
            extent = -sweep_max * frac
            rgb_t = _hex_to_rgb01(str(it.get("track_hex") or "#e5e7eb"))
            c.setStrokeColorRGB(*rgb_t)
            c.setLineWidth(7.2)
            c.circle(cx, cy, r, stroke=1, fill=0)

            rgb = _hex_to_rgb01(str(it.get("color_hex") or "#7c3aed"))
            c.setStrokeColorRGB(rgb[0] * 0.95, rgb[1] * 0.95, rgb[2] * 0.95)
            c.setLineWidth(8.0)
            x1, y1 = cx - r, cy - r
            x2, y2 = cx + r, cy + r
            c.arc(x1, y1, x2, y2, 90, extent)

        c.restoreState()

        leg_x = 228.0
        y0 = self.height - 36.0
        for i, it in enumerate(self._items):
            iy = y0 - i * 30.0
            ch = str(it.get("nombre") or "")[:34]
            qty = int(it.get("cantidad") or 0)
            px = str(it.get("precio_txt") or "")
            line = f"{ch}  ·  {qty} u.  ·  {px}"
            rgb = _hex_to_rgb01(str(it.get("color_hex") or "#7c3aed"))
            c.saveState()
            c.setFillColorRGB(*rgb)
            c.circle(leg_x + 4, iy + 3.2, 4.8, stroke=0, fill=1)
            c.setFillColorRGB(0.12, 0.16, 0.22)
            c.setFont("Helvetica-Bold", 8.2)
            c.drawString(leg_x + 14, iy, line)
            c.restoreState()


def _reporte_top_categoria_ventas(fd: date, fh: date) -> str:
    row = (
        DetalleVenta.objects.filter(
            venta__fecha_venta__gte=fd,
            venta__fecha_venta__lte=fh,
            venta__estado__in=[Venta.Estado.ABIERTA, Venta.Estado.FACTURADA],
        )
        .values("producto__categoria")
        .annotate(u=Sum("cantidad"))
        .order_by("-u")
        .first()
    )
    return ((row or {}).get("producto__categoria") or "").strip()


def _reporte_dominio_marca_por_categoria(cat_dom: str) -> tuple[list[str], list[float], int]:
    """Marcas dentro de una categoría de catálogo (conteo SKU activos)."""
    cat_dom = (cat_dom or "").strip()
    if not cat_dom:
        return [], [], 0
    rows = list(
        Producto.objects.filter(activo=True, categoria__iexact=cat_dom)
        .values("marca")
        .annotate(n=Count("id"))
        .order_by("-n")
    )
    labels: list[str] = []
    vals: list[float] = []
    for r in rows:
        m = (r["marca"] or "").strip() or "Sin marca"
        labels.append(m)
        vals.append(float(r["n"]))
    total = int(sum(vals)) if vals else 0
    return labels, vals, total


def _reporte_top5_productos_volumen(fd: date, fh: date) -> list[dict]:
    q = (
        DetalleVenta.objects.filter(
            venta__fecha_venta__gte=fd,
            venta__fecha_venta__lte=fh,
            venta__estado__in=[Venta.Estado.ABIERTA, Venta.Estado.FACTURADA],
        )
        .values(
            "producto__id",
            "producto__nombre",
            "producto__precio_venta",
            "producto__costo_unitario",
        )
        .annotate(cantidad=Sum("cantidad"))
        .order_by("-cantidad")[:5]
    )
    return list(q)


def _reporte_pdf_compute_col_widths(headers: list[str], *, total_mm: float = 180.0):
    """Anchos de columna en mm: más espacio a nombre/cliente/correo; ID y marcas más estrechos."""
    from reportlab.lib.units import mm as mm_u

    if not headers:
        return None
    weights: list[float] = []
    for h in headers:
        t = (h or "").strip().lower()
        if t == "id":
            w = 14.0
        elif "código" in t or "codigo" in t:
            w = 24.0
        elif "factura" in t:
            w = 22.0
        elif "nombre" in t or "producto" in t or "cliente" in t:
            w = 64.0
        elif "correo" in t or "email" in t:
            w = 42.0
        elif "categoría" in t or "categoria" in t:
            w = 28.0
        elif "marca" in t:
            w = 20.0
        elif "fecha" in t:
            w = 22.0
        elif "estado" in t:
            w = 20.0
        elif "documento" in t:
            w = 26.0
        elif "precio" in t or "monto" in t or "total" in t or "cop" in t:
            w = 26.0
        elif "stock" in t or "cantidad" in t or "pedidos" in t or "unidades" in t:
            w = 18.0
        else:
            w = 22.0
        weights.append(w)
    scale = total_mm / sum(weights)
    return [w * scale * mm_u for w in weights]


def _reporte_logo_path() -> Path | None:
    """Resuelve logo para PDF: BASE_DIR suele ser la carpeta Technova del proyecto."""
    base = Path(getattr(settings, "BASE_DIR", Path.cwd()))
    for parts in (
        ("static", "frontend", "imagenes", "logo-technova.png"),
        ("Technova", "static", "frontend", "imagenes", "logo-technova.png"),
    ):
        p = base.joinpath(*parts)
        if p.is_file():
            return p
    return None


def _metodo_pago_label(clave: str) -> str:
    for k, label in MedioPago.Metodo.choices:
        if k == clave:
            return str(label)
    return clave


def _reporte_label_corta(texto: str, max_len: int = 14) -> str:
    t = (texto or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


# Paleta marca TechNova (ejecutivo / referencia Ariova-BI)
_REPORTE_CHART_COLORS_HEX = (
    "#6f42c1",
    "#007bff",
    "#e83e8c",
    "#5a32a3",
    "#6610f2",
    "#17a2b8",
    "#fd7e14",
    "#20c997",
)

# Gráficas lineales / área (referencia BI neon — serie 1 morado, serie 2 azul)
_REPORTE_LINE_PRIMARY_HEX = "#6f42c1"
_REPORTE_LINE_SECONDARY_HEX = "#007bff"
_REPORTE_LINE_AREA_ALPHA_PEAK = 0.4


def _reporte_pdf_header_columna_derecha(h: str) -> bool:
    """Alineación derecha en tablas PDF para montos, cantidades y similares."""
    t = (h or "").strip().lower()
    if not t:
        return False
    claves = (
        "precio",
        "monto",
        "total",
        "(cop)",
        "cop)",
        "stock",
        "cantidad",
        "unidades",
        "pedidos",
        "valor",
        "ingreso",
        "recaud",
        "exitoso",
        "fallido",
    )
    return any(c in t for c in claves)


def _reporte_pdf_graficas_flowables(
    graficas: list[dict],
    *,
    h2_style,
    muted_style,
    frame_w_pt: float | None = None,
    chart_scale: float = 1.0,
) -> list:
    """
    Construye flowables de gráficas para el PDF (barras, líneas, pastel, rosca, barras agrupadas).
    Ítem típico: { "titulo", "tipo", "labels", "valores" } o barras agrupadas con "series".
    """
    if not graficas:
        return []
    try:
        from reportlab.graphics import renderPDF
        from reportlab.graphics.charts.barcharts import VerticalBarChart
        from reportlab.graphics.charts.legends import Legend
        from reportlab.graphics.charts.piecharts import Pie
        from reportlab.graphics.shapes import Circle, Drawing, Ellipse, Line, Path, Polygon, Rect, String
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle
    except Exception:  # noqa: BLE001
        return []

    from web.reporte_pdf_graficas import reporte_pdf_draw_line as _draw_line
    from web.reporte_pdf_graficas import reporte_pdf_draw_multi_area as _draw_multi_area

    from reportlab.lib.pagesizes import A4 as _A4_pdf
    from reportlab.lib.units import mm as _mm_pdf

    fw = float(frame_w_pt) if frame_w_pt is not None else float(_A4_pdf[0] - 14 * _mm_pdf - 14 * _mm_pdf - 15)
    out: list = []
    chart_canvas_w = fw * 0.98

    class _ScaledDrawingFlowable(Flowable):
        """Escala el drawing (p. ej. −15 %) para compactar el PDF."""

        def __init__(self, drawing: Drawing, scale: float):
            self.drawing = drawing
            self.scale = float(scale)
            self.h = float(drawing.height) * self.scale
            self.w = float(drawing.width) * self.scale

        def wrap(self, availWidth, availHeight):  # noqa: ANN001
            return self.w, self.h

        def draw(self):
            self.canv.saveState()
            self.canv.scale(self.scale, self.scale)
            renderPDF.draw(self.drawing, self.canv, 0, 0)
            self.canv.restoreState()

    class _DrawingFlowable(Flowable):
        def __init__(self, drawing: Drawing):
            self.drawing = drawing
            self.h = float(drawing.height)
            self.w = float(drawing.width)

        def wrap(self, availWidth, availHeight):  # noqa: ANN001
            return self.w, self.h

        def draw(self):
            renderPDF.draw(self.drawing, self.canv, 0, 0)

    st_rosca_leg = ParagraphStyle(
        "rosca_leg_rep",
        parent=muted_style,
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )

    def _drawing_flowable(drawing: Drawing) -> Flowable:
        return _DrawingFlowable(drawing)

    def _parse_dominio_marca(spec: dict) -> tuple[list, list, float, str, int] | None:
        raw_lbl = [str(x) for x in (spec.get("labels") or [])]
        try:
            vals = [float(x) for x in (spec.get("valores") or [])]
        except (TypeError, ValueError):
            return None
        pairs = [(str(l).strip() or "Sin marca", float(v)) for l, v in zip(raw_lbl, vals) if float(v) > 0]
        if not pairs:
            return None
        names = [p[0] for p in pairs]
        vals2 = [p[1] for p in pairs]
        total = sum(vals2)
        if total <= 0:
            return None
        cat = (spec.get("categoria_etiqueta") or "").strip() or "Categoría"
        total_cat = int(spec.get("total_categoria") or round(total))
        cat_short = _reporte_label_corta(cat, 22)
        return names, vals2, total, cat_short, total_cat

    def _draw_dominio_marca_pie_only(spec: dict) -> Drawing | None:
        """Rosca sin leyenda (la leyenda va en columna a la derecha en el layout espejo)."""
        parsed = _parse_dominio_marca(spec)
        if not parsed:
            return None
        _, vals2, _tot, cat_short, total_cat = parsed
        pie_w = 165  # +25% respecto a ~132
        d_w, d_h = 300, 280
        cx = d_w / 2
        cy = d_h / 2.0
        d = Drawing(d_w, d_h)
        pc = Pie()
        pc.x = cx - pie_w / 2
        pc.y = cy - pie_w / 2
        pc.width = pie_w
        pc.height = pie_w
        pc.sameRadii = True
        pc.startAngle = 90
        pc.data = vals2
        pc.labels = [""] * len(vals2)
        pc.simpleLabels = 0
        pc.checkLabelOverlap = 0
        pc.sideLabels = 0
        pc.slices.strokeWidth = 1.0
        pc.slices.strokeColor = colors.white
        pc.slices.fontSize = 1
        for i in range(len(vals2)):
            pc.slices[i].fillColor = _palette_color(i)
            pc.slices[i].strokeColor = colors.white
            pc.slices[i].strokeWidth = 1.0
        d.add(
            Ellipse(
                cx,
                cy - 4,
                pie_w * 0.48,
                pie_w * 0.14,
                fillColor=colors.Color(0, 0, 0, alpha=0.1),
                strokeColor=None,
                strokeWidth=0,
            )
        )
        d.add(pc)
        rhole = min(pc.width, pc.height) * 0.36
        d.add(
            Circle(
                cx,
                cy,
                rhole,
                fillColor=colors.white,
                strokeColor=colors.HexColor("#e5e7eb"),
                strokeWidth=0.65,
            )
        )
        fs_big = 16 if len(str(total_cat)) <= 4 else 14
        d.add(
            String(
                cx,
                cy + 8,
                f"Total {cat_short}",
                textAnchor="middle",
                fontName="Helvetica-Bold",
                fontSize=8.5,
                fillColor=colors.HexColor("#475569"),
            )
        )
        d.add(
            String(
                cx,
                cy - 8,
                str(total_cat),
                textAnchor="middle",
                fontName="Helvetica-Bold",
                fontSize=fs_big,
                fillColor=colors.HexColor("#6f42c1"),
            )
        )
        d.add(
            String(
                cx,
                cy - 24,
                "SKU",
                textAnchor="middle",
                fontName="Helvetica",
                fontSize=7.5,
                fillColor=colors.HexColor("#94a3b8"),
            )
        )
        return d

    def _platypus_dominio_legend(names: list[str], vals2: list[float], total: float, leg_w: float) -> Table:
        from reportlab.platypus import Image as RLImage

        rows: list[list] = []
        for i, name in enumerate(names):
            v = float(vals2[i])
            col = _palette_color(i)
            dot = Drawing(12, 12)
            dot.add(Circle(6, 6, 5.2, fillColor=col, strokeColor=colors.white, strokeWidth=0.45))
            pct = 100.0 * v / total
            nm = _reporte_label_corta(name, 40)
            txt = (
                f"<b>{_xml_escape(nm)}</b>  "
                f"{int(v)} SKU  "
                f"<font color='#64748b'>({pct:.1f}%)</font>"
            )
            p = Paragraph(txt, st_rosca_leg)
            ip = _reporte_marca_icon_abs_path(name)
            cell_mid: Flowable | Spacer
            if ip:
                try:
                    cell_mid = RLImage(ip, width=11, height=11)
                except Exception:  # noqa: BLE001
                    cell_mid = Spacer(12, 12)
            else:
                cell_mid = Spacer(12, 12)
            rows.append([_drawing_flowable(dot), cell_mid, p])
        tw = Table(
            rows,
            colWidths=[16, 16, max(80.0, leg_w - 32)],
        )
        tw.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return tw

    def _flowable_dominio_marca_espejo(spec: dict) -> Table | None:
        """Rosca a la izquierda (grande) + leyendas a la derecha (8.5 pt)."""
        parsed = _parse_dominio_marca(spec)
        if not parsed:
            return None
        names, vals2, total, _cs, _tc = parsed
        pie = _draw_dominio_marca_pie_only(spec)
        if not pie:
            return None
        col_left = fw * 0.50
        col_right = fw * 0.50
        sc = min(float(chart_scale) * 1.25, (col_left - 14.0) / float(pie.width))
        sc = max(0.5, float(sc))
        pie_fb = _ScaledDrawingFlowable(pie, sc)
        leg = _platypus_dominio_legend(names, vals2, total, col_right - 12)
        tbl = Table([[pie_fb, leg]], colWidths=[col_left, col_right])
        tbl.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        return tbl

    def _wrap_centered(drawing: Drawing) -> Table:
        df = _ScaledDrawingFlowable(drawing, chart_scale)
        tbl = Table([[df]], colWidths=[chart_canvas_w])
        tbl.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return tbl

    def _wrap_any_chart(obj):  # noqa: ANN001
        if isinstance(obj, Drawing):
            return _wrap_centered(obj)
        return Table(
            [[obj]],
            colWidths=[chart_canvas_w],
            style=TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )

    def _wrap_full_width_drawing(piece) -> Table:  # noqa: ANN001
        """Escala una gráfica vectorial al ancho útil (p. ej. ranking de facturación)."""
        if isinstance(piece, Drawing):
            fit = min(float(chart_scale) * 1.25, max(0.52, (fw - 8.0) / float(piece.width)))
            df = _ScaledDrawingFlowable(piece, fit)
            tbl = Table([[df]], colWidths=[fw])
            tbl.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            return tbl
        return _wrap_any_chart(piece)

    def _split_dom_rank_pdf(specs: list[dict]) -> tuple[dict | None, dict | None, list[dict]]:
        dom = None
        rank = None
        rest: list[dict] = []
        for s in specs:
            t = (s.get("tipo") or "").lower()
            tit = (s.get("titulo") or "").lower()
            if t == "rosca_dominio_marca" and dom is None:
                dom = s
            elif t == "barras_horizontales" and "ranking" in tit and rank is None:
                rank = s
            else:
                rest.append(s)
        return dom, rank, rest

    def _wrap_for_col(piece, col_w: float):
        """Escala un Drawing para caber en una columna (layout 2×1)."""
        if isinstance(piece, Drawing):
            fit = min(float(chart_scale) * 1.25, max(0.38, (float(col_w) - 8.0) / float(piece.width)))
            df = _ScaledDrawingFlowable(piece, fit)
            tbl = Table([[df]], colWidths=[col_w])
            tbl.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 2),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            return tbl
        return Table(
            [[piece]],
            colWidths=[col_w],
            style=TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]
            ),
        )

    def _palette_color(i: int):
        return colors.HexColor(_REPORTE_CHART_COLORS_HEX[i % len(_REPORTE_CHART_COLORS_HEX)])

    def _draw_bar(labels: list[str], vals: list[float]) -> Drawing | None:
        if not vals or len(labels) != len(vals):
            return None
        d = Drawing(460, 218)
        bc = VerticalBarChart()
        bc.x = 48
        bc.y = 52
        bc.height = 118
        bc.width = 364
        bc.data = [vals]
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.strokeColor = colors.HexColor("#cbd5e1")
        bc.categoryAxis.strokeWidth = 0.5
        bc.categoryAxis.labels.fontName = "Helvetica"
        bc.categoryAxis.labels.fontSize = 8
        bc.categoryAxis.labels.fillColor = colors.HexColor("#334155")
        if len(labels) > 6:
            bc.categoryAxis.labels.angle = 35

        va = bc.valueAxis
        va.valueMin = 0
        m = max(vals) if vals else 0
        va.valueMax = None if m <= 0 else m * 1.12
        va.visibleGrid = 1
        va.gridStrokeColor = colors.HexColor("#e2e8f0")
        va.gridStrokeWidth = 0.6
        va.strokeColor = colors.HexColor("#94a3b8")
        va.strokeWidth = 0.5
        va.labels.fontName = "Helvetica"
        va.labels.fontSize = 8
        va.labels.fillColor = colors.HexColor("#64748b")

        for i in range(len(vals)):
            bc.bars[(0, i)].fillColor = _palette_color(i)
            bc.bars[(0, i)].strokeColor = colors.white
            bc.bars[(0, i)].strokeWidth = 0.35

        bc.barLabelFormat = "%.0f"
        bc.barLabels.fontName = "Helvetica"
        bc.barLabels.fontSize = 7
        bc.barLabels.fillColor = colors.HexColor("#1e293b")
        d.add(bc)
        return d

    def _draw_bar_horizontal(labels: list[str], vals: list[float]) -> Drawing | None:
        """Barras horizontales a ancho de página: categoría encima de la barra, COP a la derecha."""
        if not vals or len(labels) != len(vals):
            return None
        n = len(vals)
        m = max(float(x) for x in vals) if vals else 0.0
        if m <= 0:
            return None
        dw = max(520.0, float(fw) * 0.96)
        bar_h = 28.0
        lbl_gap = 11.0
        gap = 16.0
        row_h = lbl_gap + bar_h + gap
        bar_x0 = 130.0
        margin_r = 58.0
        bar_w_max = max(220.0, dw - bar_x0 - margin_r)
        val_right = dw - 16.0
        y0 = 38.0
        d_h = min(440.0, y0 + float(n) * row_h + 40.0)
        d = Drawing(dw, d_h)
        d.add(
            Line(
                bar_x0,
                y0 - 4,
                bar_x0 + bar_w_max,
                y0 - 4,
                strokeColor=colors.HexColor("#e8ecf4"),
                strokeWidth=0.45,
            )
        )
        for i in range(n):
            v = float(vals[i])
            y_bar = y0 + float(i) * row_h
            bw = (v / m) * bar_w_max
            strips = 56
            for j in range(strips):
                wj = bw / strips if strips else bw
                xj = bar_x0 + j * wj
                t = (j + 0.5) / max(strips, 1)
                col = _lerp_color_hex("#6f42c1", "#007bff", t)
                d.add(
                    Rect(
                        xj,
                        y_bar,
                        max(wj + 0.15, 0.28),
                        bar_h,
                        fillColor=col,
                        strokeColor=None,
                        strokeWidth=0,
                    )
                )
            d.add(
                Rect(
                    bar_x0,
                    y_bar,
                    bw,
                    bar_h,
                    fillColor=None,
                    strokeColor=colors.HexColor("#e2e8f0"),
                    strokeWidth=0.5,
                )
            )
            lbl = _reporte_label_corta(labels[i], 52)
            d.add(
                String(
                    bar_x0,
                    y_bar + bar_h + 9,
                    lbl,
                    fontName="Helvetica-Bold",
                    fontSize=8.5,
                    fillColor=colors.HexColor("#1e293b"),
                )
            )
            try:
                val_txt = _cop(Decimal(str(int(round(v)))))
            except Exception:  # noqa: BLE001
                val_txt = f"${v:,.0f}".replace(",", ".")
            d.add(
                String(
                    val_right,
                    y_bar + bar_h * 0.35,
                    val_txt,
                    textAnchor="end",
                    fontName="Helvetica-Bold",
                    fontSize=8.5,
                    fillColor=colors.HexColor("#0f172a"),
                )
            )
        return d

    def _draw_pie(labels: list[str], vals: list[float], *, donut: bool = False) -> Drawing | None:
        pairs = [(str(l).strip(), float(v)) for l, v in zip(labels, vals) if float(v) > 0]
        if not pairs:
            return None
        names = [p[0] for p in pairs]
        vals2 = [p[1] for p in pairs]
        total = sum(vals2)
        if total <= 0:
            return None

        d_w, d_h = 460, 268
        d = Drawing(d_w, d_h)
        pie_w = 128
        pc = Pie()
        pc.x = (d_w - pie_w) / 2
        pc.y = 118
        pc.width = pie_w
        pc.height = pie_w
        pc.sameRadii = True
        pc.startAngle = 90
        pc.data = vals2
        pc.labels = [f"{100.0 * v / total:.0f}%" for v in vals2]
        pc.simpleLabels = 1
        pc.slices.strokeWidth = 0.75
        pc.slices.strokeColor = colors.white
        pc.slices.fontName = "Helvetica-Bold"
        pc.slices.fontSize = 8
        pc.slices.fontColor = colors.HexColor("#0f172a")
        for i in range(len(vals2)):
            pc.slices[i].fillColor = _palette_color(i)
            pc.slices[i].strokeColor = colors.white
            pc.slices[i].strokeWidth = 0.75

        leg = Legend()
        leg.x = 40
        leg.y = 12
        leg.boxAnchor = "sw"
        leg.fontName = "Helvetica"
        leg.fontSize = 8
        leg.leading = 10
        leg.dx = 9
        leg.dy = 9
        leg.dxTextSpace = 5
        leg.deltax = 215
        leg.deltay = 11
        leg.columnMaximum = 3
        leg.strokeWidth = 0
        leg.strokeColor = None
        leg.colorNamePairs = [
            (
                _palette_color(i),
                f"{_reporte_label_corta(names[i], 34)}  ({100.0 * vals2[i] / total:.1f}%)",
            )
            for i in range(len(vals2))
        ]
        cx = pc.x + pc.width / 2
        cy = pc.y + pc.height / 2
        d.add(
            Ellipse(
                cx,
                cy - 4,
                pc.width * 0.46,
                pc.height * 0.13,
                fillColor=colors.Color(0, 0, 0, alpha=0.1),
                strokeColor=None,
                strokeWidth=0,
            )
        )
        d.add(pc)
        if donut:
            rh = min(pc.width, pc.height) * 0.44
            d.add(
                Circle(
                    cx,
                    cy,
                    rh,
                    fillColor=colors.white,
                    strokeColor=colors.HexColor("#e8eaed"),
                    strokeWidth=0.45,
                )
            )
            tot_disp = f"{int(round(total))}"
            d.add(
                String(
                    cx,
                    cy + 5,
                    "Total",
                    textAnchor="middle",
                    fontName="Helvetica-Bold",
                    fontSize=9,
                    fillColor=colors.HexColor("#475569"),
                )
            )
            d.add(
                String(
                    cx,
                    cy - 10,
                    tot_disp,
                    textAnchor="middle",
                    fontName="Helvetica-Bold",
                    fontSize=18,
                    fillColor=colors.HexColor("#6f42c1"),
                )
            )
        d.add(leg)
        return d

    def _draw_grouped_bar(labels: list[str], series: list[tuple[str, list[float]]]) -> Drawing | None:
        if len(labels) < 1 or len(series) < 2:
            return None
        data_rows = [list(map(float, s[1])) for s in series]
        if any(len(r) != len(labels) for r in data_rows):
            return None
        d = Drawing(460, 248)
        bc = VerticalBarChart()
        bc.x = 44
        bc.y = 78
        bc.height = 112
        bc.width = 368
        bc.data = data_rows
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.strokeColor = colors.HexColor("#cbd5e1")
        bc.categoryAxis.strokeWidth = 0.5
        bc.categoryAxis.labels.fontName = "Helvetica"
        bc.categoryAxis.labels.fontSize = 7.5
        bc.categoryAxis.labels.fillColor = colors.HexColor("#334155")
        if len(labels) > 8:
            bc.categoryAxis.labels.angle = 35
        bc.groupSpacing = 5
        bc.barSpacing = 2
        va = bc.valueAxis
        va.valueMin = 0
        m = max((max(r) if r else 0) for r in data_rows)
        va.valueMax = None if m <= 0 else m * 1.18
        va.visibleGrid = 1
        va.gridStrokeColor = colors.HexColor("#e2e8f0")
        va.gridStrokeWidth = 0.6
        va.strokeColor = colors.HexColor("#94a3b8")
        va.labels.fontName = "Helvetica"
        va.labels.fontSize = 8
        va.labels.fillColor = colors.HexColor("#64748b")
        for si in range(len(data_rows)):
            for ci in range(len(labels)):
                bc.bars[(si, ci)].fillColor = _palette_color(si * 4 + ci % 3)
                bc.bars[(si, ci)].strokeColor = colors.white
                bc.bars[(si, ci)].strokeWidth = 0.35
        bc.barLabelFormat = "%.0f"
        bc.barLabels.fontName = "Helvetica"
        bc.barLabels.fontSize = 6
        bc.barLabels.fillColor = colors.HexColor("#1e293b")
        d.add(bc)
        leg = Legend()
        leg.x = 44
        leg.y = 18
        leg.boxAnchor = "sw"
        leg.fontName = "Helvetica"
        leg.fontSize = 8
        leg.leading = 10
        leg.dx = 8
        leg.dy = 8
        leg.dxTextSpace = 4
        leg.deltax = 120
        leg.deltay = 11
        leg.columnMaximum = 4
        leg.strokeWidth = 0
        leg.strokeColor = None
        leg.colorNamePairs = [(_palette_color(si * 4), str(s[0])[:32]) for si, s in enumerate(series)]
        d.add(leg)
        return d

    def _piece_from_spec(spec: dict) -> Drawing | Flowable | None:
        tipo = (spec.get("tipo") or "barras").strip().lower()
        raw_labels = [str(x) for x in (spec.get("labels") or [])]
        try:
            vals = [float(x) for x in (spec.get("valores") or [])]
        except (TypeError, ValueError):
            vals = []
        if tipo in ("pastel", "pie", "piechart", "rosca", "donut", "doughnut", "rosca_dominio_marca"):
            labels = raw_labels
        else:
            labels = [_reporte_label_corta(x, 20) for x in raw_labels]
        piece: Drawing | Flowable | None = None

        if tipo in ("lineas_area_multiserie", "area_multiserie", "lineas_multiples"):
            raw_series = spec.get("series") or []
            series_pairs2: list[tuple[str, list[float]]] = []
            for s in raw_series:
                if not isinstance(s, dict):
                    continue
                sl = str(s.get("label") or "")
                try:
                    sv = [float(x) for x in (s.get("valores") or [])]
                except (TypeError, ValueError):
                    continue
                series_pairs2.append((sl, sv))
            labs_m = [_reporte_label_corta(x, 20) for x in raw_labels]
            if len(series_pairs2) >= 2 and labs_m and all(len(labs_m) == len(s[1]) for s in series_pairs2):
                piece = _draw_multi_area(labs_m, series_pairs2)

        elif tipo in ("radial_top5", "top5_radial", "ranking_radial"):
            raw_items = spec.get("items") or []
            parsed_rad: list[dict] = []
            max_q = 0
            for it in raw_items:
                if not isinstance(it, dict):
                    continue
                q = int(it.get("cantidad") or 0)
                max_q = max(max_q, q)
                parsed_rad.append(it)
            if max_q <= 0 and parsed_rad:
                max_q = 1
            rad_colors = ["#6f42c1", "#007bff", "#e83e8c", "#5a32a3", "#6610f2"]
            track_hex = ["#ede9fe", "#dbeafe", "#fce7f3", "#f3e8ff", "#e0e7ff"]
            built: list[dict] = []
            for idx, it in enumerate(parsed_rad):
                if not isinstance(it, dict):
                    continue
                q = int(it.get("cantidad") or 0)
                frac = (q / max_q) if max_q else 1.0
                built.append(
                    {
                        "nombre": str(it.get("nombre") or "—"),
                        "cantidad": q,
                        "precio_txt": str(it.get("precio_txt") or "—"),
                        "arc_frac": frac,
                        "color_hex": str(it.get("color_hex") or rad_colors[idx % len(rad_colors)]),
                        "track_hex": str(it.get("track_hex") or track_hex[idx % len(track_hex)]),
                    }
                )
            if built:
                piece = _ReporteRadialTop5Flowable(built)

        elif tipo in ("rosca_dominio_marca", "donut_dominio_marca"):
            piece = _flowable_dominio_marca_espejo(spec)

        elif tipo in ("barras_agrupadas", "grouped_bar", "barras_grupo"):
            raw_series = spec.get("series") or []
            series_pairs: list[tuple[str, list[float]]] = []
            for s in raw_series:
                if not isinstance(s, dict):
                    continue
                sl = str(s.get("label") or "")
                try:
                    sv = [float(x) for x in (s.get("valores") or [])]
                except (TypeError, ValueError):
                    continue
                series_pairs.append((sl, sv))
            if len(series_pairs) >= 2 and labels and all(len(labels) == len(s[1]) for s in series_pairs):
                piece = _draw_grouped_bar(labels, series_pairs)
        elif len(labels) == len(vals):
            if tipo in ("barras_horizontales", "horizontal_bar", "bar_h", "barras_h"):
                piece = _draw_bar_horizontal(labels, vals)
            elif tipo in ("barras", "bar"):
                piece = _draw_bar(labels, vals)
            elif tipo in ("lineas", "linea", "line"):
                piece = _draw_line(labels, vals)
            elif tipo in ("pastel", "pie", "piechart"):
                piece = _draw_pie(labels, vals, donut=False)
            elif tipo in ("rosca", "donut", "doughnut"):
                piece = _draw_pie(labels, vals, donut=True)
            else:
                piece = _draw_bar(labels, vals)
        return piece

    dom_s, rank_s, rest_specs = _split_dom_rank_pdf(list(graficas))
    _sec_gap = 20

    if dom_s and rank_s:
        p_dom = _flowable_dominio_marca_espejo(dom_s)
        p_rank = _piece_from_spec(rank_s)
        if p_dom and p_rank:
            out.append(
                Paragraph(f"<b>{_xml_escape((dom_s.get('titulo') or 'Gráfica').strip())}</b>", h2_style)
            )
            out.append(Spacer(1, 8))
            out.append(p_dom)
            out.append(Spacer(1, _sec_gap))
            out.append(
                Paragraph(f"<b>{_xml_escape((rank_s.get('titulo') or 'Gráfica').strip())}</b>", h2_style)
            )
            out.append(Spacer(1, 8))
            out.append(_wrap_full_width_drawing(p_rank))
            out.append(Spacer(1, _sec_gap))

    for spec in rest_specs:
        titulo = (spec.get("titulo") or "Gráfica").strip()
        piece = _piece_from_spec(spec)
        if piece is None:
            out.append(Paragraph(f"<i>{titulo}</i> — sin datos suficientes para graficar.", muted_style))
            out.append(Spacer(1, _sec_gap))
            continue
        out.append(Paragraph(f"<b>{titulo}</b>", h2_style))
        out.append(Spacer(1, 8))
        out.append(_wrap_any_chart(piece))
        out.append(Spacer(1, _sec_gap))
    return out


def _reporte_exec_canvas_factory(*, generado_por: str):
    """Canvas con pie fijo: numeración 'Página i de n' y marca TechNova."""

    from reportlab.lib import colors as rl_colors
    from reportlab.lib.units import mm as rl_mm
    from reportlab.pdfgen import canvas as pdfcanvas

    gp_short = (generado_por or "").strip()[:90]

    class _ReporteExecCanvas(pdfcanvas.Canvas):
        def __init__(self, *args, **kwargs):
            pdfcanvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            n_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._rep_draw_footer(n_pages)
                pdfcanvas.Canvas.showPage(self)
            pdfcanvas.Canvas.save(self)

        def _rep_draw_footer(self, n_pages: int) -> None:
            w, _h = self._pagesize
            lm = 14 * rl_mm
            rm = 14 * rl_mm
            y_line = 12 * rl_mm
            y_txt = 7.2 * rl_mm
            y_sub = 4.0 * rl_mm
            self.saveState()
            self.setStrokeColor(rl_colors.HexColor("#d1d5db"))
            self.setLineWidth(0.55)
            self.line(lm, y_line, w - rm, y_line)
            self.setFont("Helvetica", 8)
            self.setFillColor(rl_colors.HexColor("#6b7280"))
            self.drawString(lm, y_txt, "Reporte generado automáticamente por TechNova")
            self.setFont("Helvetica-Bold", 8.5)
            self.setFillColor(rl_colors.HexColor("#4b5563"))
            self.drawRightString(w - rm, y_txt, f"Página {self._pageNumber} de {n_pages}")
            if gp_short:
                self.setFont("Helvetica-Oblique", 7.5)
                self.setFillColor(rl_colors.HexColor("#9ca3af"))
                self.drawCentredString(w / 2, y_sub, f"Generado por: {gp_short}")
            self.restoreState()

    return _ReporteExecCanvas


def _reporte_build_pdf(titulo: str, filtros: list[str], headers: list[str], rows: list[list[str]]) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:
        raise RuntimeError("No se encontró la librería 'reportlab'.") from exc

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(f"<b>{titulo}</b>", styles["Title"]),
        Spacer(1, 6),
        Paragraph(f"Fecha de generación: {timezone.localtime().strftime('%d/%m/%Y %H:%M')}", styles["Normal"]),
        Spacer(1, 4),
        Paragraph(" | ".join(filtros) if filtros else "Sin filtros aplicados.", styles["Normal"]),
        Spacer(1, 10),
    ]
    data = [headers] + rows
    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#eef2ff")]),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()


def _reporte_build_pdf_v2(
    *,
    titulo: str,
    subtitulo: str,
    rango: str,
    kpis: list,
    secciones: list[tuple[str, list[str], list[list[str]]]],
    graficas: list[dict] | None = None,
    generado_por: str = "",
    cajas_impacto: list[tuple[str, str]] | None = None,
) -> bytes:
    """
    PDF ejecutivo TechNova: franja de marca, KPIs hero, gráficas vectoriales, tablas cebradas y pie con paginación.
    """
    try:
        from reportlab.graphics import renderPDF
        from reportlab.graphics.shapes import Circle, Drawing, Line, Rect
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Flowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception as exc:
        raise RuntimeError("No se encontró la librería 'reportlab'.") from exc

    buffer = BytesIO()
    _canvas_cls = _reporte_exec_canvas_factory(generado_por=generado_por)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm + 15,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=titulo,
        canvasmaker=_canvas_cls,
    )
    # Ancho útil del marco (100 % del área imprimible). Antes se mezclaban 174/180 mm con padding en pt,
    # y la fila del encabezado superaba el ancho interior → texto cortado a la derecha.
    frame_w = float(A4[0] - doc.leftMargin - doc.rightMargin)
    frame_w_mm = float(frame_w / mm)

    styles = getSampleStyleSheet()
    c_slate = colors.HexColor("#334155")
    c_muted = colors.HexColor("#64748b")
    c_line = colors.HexColor("#e5e7eb")
    c_brand = colors.HexColor("#6f42c1")
    c_brand_blue = colors.HexColor("#007bff")
    c_brand_pink = colors.HexColor("#e83e8c")
    c_head_tbl = colors.HexColor("#5a32a3")
    c_row_alt = colors.HexColor("#f9fafb")

    h2 = ParagraphStyle(
        "t_h2_rep",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=c_brand,
        spaceBefore=6,
        spaceAfter=4,
    )
    muted = ParagraphStyle(
        "t_muted_rep",
        parent=styles["Normal"],
        fontSize=9.5,
        textColor=c_muted,
        leading=12,
    )

    st_kpi_h = ParagraphStyle(
        "kpi_sec_hdr_rep",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#5b21b6"),
        leading=14,
        spaceBefore=0,
        spaceAfter=7,
    )
    st_kpi_lbl = ParagraphStyle(
        "kpi_lbl_rep",
        parent=styles["Normal"],
        fontSize=7,
        textColor=colors.HexColor("#64748b"),
        leading=10,
        fontName="Helvetica",
        spaceAfter=3,
    )
    st_kpi_val = ParagraphStyle(
        "kpi_val_rep",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15.5,
        textColor=colors.HexColor("#0f172a"),
        leading=17,
    )

    st_imp_lbl = ParagraphStyle(
        "imp_lbl_rep",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6b7280"),
        leading=10,
        fontName="Helvetica",
    )
    st_imp_val = ParagraphStyle(
        "imp_val_rep",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=colors.HexColor("#111827"),
        leading=17,
    )
    st_imp_val_ok = ParagraphStyle(
        "imp_val_ok_rep",
        parent=st_imp_val,
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#16a34a"),
        leading=14,
    )

    st_tbl_hdr = ParagraphStyle(
        "tbl_hdr_rep",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=colors.white,
    )
    st_tbl_cell = ParagraphStyle(
        "tbl_cell_rep",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=c_slate,
        wordWrap="CJK",
    )
    st_tbl_cell_r = ParagraphStyle(
        "tbl_cell_r_rep",
        parent=st_tbl_cell,
        alignment=2,
    )
    st_tbl_cell_long = ParagraphStyle(
        "tbl_cell_long_rep",
        parent=st_tbl_cell,
        fontSize=7.5,
        leading=10,
        textColor=c_slate,
        wordWrap="CJK",
    )

    class _BrandTopHairline(Flowable):
        def wrap(self, availWidth, availHeight):  # noqa: ANN001
            self._hair_w = availWidth
            return availWidth, 3.8

        def draw(self):
            self.canv.setStrokeColor(colors.HexColor("#6f42c1"))
            self.canv.setLineWidth(2.2)
            self.canv.line(0, 1.4, self._hair_w, 1.4)

    class _MiniDrawFb(Flowable):
        def __init__(self, drawing: Drawing):
            self.drawing = drawing
            self.h = float(drawing.height)
            self.w = float(drawing.width)

        def wrap(self, availWidth, availHeight):  # noqa: ANN001
            return self.w, self.h

        def draw(self):
            renderPDF.draw(self.drawing, self.canv, 0, 0)

    def _kpi_icon_widget(icon_key: str, tone_i: int = 0) -> Flowable:
        key = (icon_key or "dot").lower()
        W, H = 22.0, 22.0
        d = Drawing(W, H)
        tone_icons = (
            (colors.HexColor("#7c3aed"), colors.HexColor("#3b82f6"), colors.HexColor("#ddd6fe")),
            (colors.HexColor("#2563eb"), colors.HexColor("#38bdf8"), colors.HexColor("#dbeafe")),
            (colors.HexColor("#c026d3"), colors.HexColor("#f472b6"), colors.HexColor("#fce7f3")),
        )
        accent, soft, ink = tone_icons[tone_i % len(tone_icons)]
        if key in ("sku", "grid", "box", "producto"):
            for i in range(3):
                for j in range(3):
                    d.add(
                        Rect(
                            2.4 + j * 6,
                            2.4 + i * 6,
                            4.6,
                            4.6,
                            rx=0.7,
                            ry=0.7,
                            fillColor=accent if (i + j) % 2 == 0 else soft,
                            strokeColor=ink,
                            strokeWidth=0.2,
                        )
                    )
        elif key in ("money", "cop", "ingreso", "recaudo"):
            d.add(Circle(11, 11, 8.5, fillColor=accent, strokeColor=soft, strokeWidth=0.8))
            d.add(Line(11, 8, 11, 14, strokeColor=colors.white, strokeWidth=1.1))
            d.add(Line(8, 11, 14, 11, strokeColor=colors.white, strokeWidth=1.0))
        elif key in ("ticket", "avg", "promedio"):
            d.add(Rect(5, 6, 12, 10, rx=1.5, ry=1.5, fillColor=soft, strokeColor=ink, strokeWidth=0.4))
            d.add(Line(7, 9, 15, 9, strokeColor=accent, strokeWidth=0.8))
            d.add(Line(7, 11.5, 13, 11.5, strokeColor=accent, strokeWidth=0.8))
        elif key in ("users", "user", "personas"):
            d.add(Circle(8, 10, 3.2, fillColor=accent, strokeColor=colors.white, strokeWidth=0.4))
            d.add(Circle(14.5, 10, 3.2, fillColor=soft, strokeColor=colors.white, strokeWidth=0.4))
            d.add(Rect(9.5, 14, 7, 3, rx=1, ry=1, fillColor=accent, strokeColor=None, strokeWidth=0))
        elif key in ("chart", "line", "tendencia"):
            d.add(Line(4, 6, 8, 14, strokeColor=soft, strokeWidth=1.2))
            d.add(Line(8, 14, 12, 9, strokeColor=accent, strokeWidth=1.2))
            d.add(Line(12, 9, 18, 16, strokeColor=accent, strokeWidth=1.2))
        elif key in ("check", "ok", "exito"):
            d.add(Circle(11, 11, 8, fillColor=colors.HexColor("#16a34a"), strokeColor=ink, strokeWidth=0.5))
            d.add(Line(7, 11, 10, 14, strokeColor=colors.white, strokeWidth=1.4))
            d.add(Line(10, 14, 16, 8, strokeColor=colors.white, strokeWidth=1.4))
        elif key in ("fail", "error", "x"):
            d.add(Circle(11, 11, 8, fillColor=colors.HexColor("#dc2626"), strokeColor=ink, strokeWidth=0.5))
            d.add(Line(7.5, 7.5, 14.5, 14.5, strokeColor=colors.white, strokeWidth=1.3))
            d.add(Line(14.5, 7.5, 7.5, 14.5, strokeColor=colors.white, strokeWidth=1.3))
        elif key in ("clock", "time", "mes", "calendario"):
            d.add(Circle(11, 11, 8.5, fillColor=soft, strokeColor=accent, strokeWidth=0.7))
            d.add(Line(11, 11, 11, 7.5, strokeColor=accent, strokeWidth=1.1))
            d.add(Line(11, 11, 14.5, 12, strokeColor=accent, strokeWidth=1.1))
        elif key in ("card", "pago", "metodo"):
            d.add(Rect(4, 7, 14, 10, rx=1.8, ry=1.8, fillColor=accent, strokeColor=ink, strokeWidth=0.5))
            d.add(Rect(4.5, 10.5, 10, 2, fillColor=soft, strokeColor=None, strokeWidth=0))
        else:
            d.add(Circle(11, 11, 3.2, fillColor=accent, strokeColor=soft, strokeWidth=0.6))
        return _MiniDrawFb(d)

    logo_path = _reporte_logo_path()
    logo_cell: Flowable | Paragraph = Paragraph("", muted)
    if logo_path is not None:
        try:
            logo_cell = Image(str(logo_path), width=22 * mm, height=22 * mm)
        except Exception:  # noqa: BLE001
            logo_cell = Paragraph("", muted)

    gen_txt = timezone.localtime().strftime("%d/%m/%Y %H:%M")
    rango_txt = (rango or "").strip()
    if rango_txt.lower().startswith("rango:"):
        rango_val = rango_txt
    else:
        rango_val = rango_txt if rango_txt else "—"
    gp_lbl = (generado_por or "").strip() or "Sistema Technova"

    st_meta_lbl = ParagraphStyle(
        "rep_meta_lbl",
        parent=styles["Normal"],
        alignment=2,
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=2,
    )
    st_meta_lbl_first = ParagraphStyle(
        "rep_meta_lbl_first",
        parent=st_meta_lbl,
        spaceBefore=0,
    )
    st_meta_lbl_gap = ParagraphStyle(
        "rep_meta_lbl_gap",
        parent=st_meta_lbl,
        spaceBefore=4,
    )
    st_meta_val = ParagraphStyle(
        "rep_meta_val",
        parent=styles["Normal"],
        alignment=2,
        fontName="Helvetica",
        fontSize=7.5,
        leading=11,
        textColor=colors.HexColor("#334155"),
        spaceAfter=0,
    )

    enc_pad_left = 12
    enc_pad_right = 12 + 15
    stripe_w = 6 * mm
    logo_col_w = 28 * mm
    content_inner = frame_w - enc_pad_left - enc_pad_right
    inner_w = content_inner - stripe_w
    meta_col_w = inner_w - logo_col_w

    meta_table = Table(
        [
            [Paragraph("Emisión:", st_meta_lbl_first)],
            [Paragraph(_xml_escape(gen_txt), st_meta_val)],
            [Paragraph("Autor:", st_meta_lbl_gap)],
            [Paragraph(_xml_escape(gp_lbl), st_meta_val)],
            [Paragraph("Período:", st_meta_lbl_gap)],
            [Paragraph(_xml_escape(rango_val), st_meta_val)],
        ],
        colWidths=[meta_col_w],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 22),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 1), (0, 1), 4),
                ("BOTTOMPADDING", (0, 3), (0, 3), 4),
            ]
        )
    )

    st_title_line = ParagraphStyle(
        "rep_title_line",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=15,
        textColor=colors.HexColor("#111827"),
        spaceBefore=0,
        spaceAfter=0,
    )
    title_sub_block = Paragraph(
        f"<b>{_xml_escape(str(titulo or 'Reporte'))}</b> "
        f"<font name='Helvetica-Bold' size='9' color='#6f42c1'> — {_xml_escape(str(subtitulo or 'Business Intelligence'))}</font>",
        st_title_line,
    )

    inner_top = Table([[logo_cell, meta_table]], colWidths=[logo_col_w, meta_col_w])
    inner_top.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    inner_card = Table(
        [[inner_top], [title_sub_block]],
        colWidths=[inner_w],
    )
    inner_card.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9f9f9")),
                ("ROUNDEDCORNERS", [12, 12, 12, 12]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (0, 0), 4),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 2),
            ]
        )
    )

    stripe = Table([[Paragraph("", muted)]], colWidths=[stripe_w])
    stripe.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), c_brand),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    enc_row = Table([[stripe, inner_card]], colWidths=[stripe_w, inner_w])
    enc_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    encabezado_tbl = Table([[enc_row]], colWidths=[frame_w])
    encabezado_tbl.setStyle(
        TableStyle(
            [
                ("ROUNDEDCORNERS", [14, 14, 14, 14]),
                ("BOX", (0, 0), (-1, -1), 0.65, colors.HexColor("#d1d5db")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9f9f9")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), enc_pad_left),
                ("RIGHTPADDING", (0, 0), (-1, -1), enc_pad_right),
            ]
        )
    )

    kpi_tone_bg = (
        colors.HexColor("#faf8ff"),
        colors.HexColor("#f0f7ff"),
        colors.HexColor("#fff7fb"),
    )
    kpi_tone_border = (
        colors.HexColor("#e4dcff"),
        colors.HexColor("#cce4ff"),
        colors.HexColor("#ffd6ef"),
    )
    kpi_tone_bar = (
        colors.HexColor("#7c3aed"),
        colors.HexColor("#2563eb"),
        colors.HexColor("#db2777"),
    )
    kpi_tone_val_hex = ("#4c1d95", "#1e3a8a", "#9d174d")

    def _kpi_cell(
        label: str,
        value: str,
        icon_key: str,
        col_w: float,
        tone_i: int,
    ) -> Table:
        ti = tone_i % len(kpi_tone_bg)
        icon_w = _kpi_icon_widget(icon_key, ti)
        txt_col_w = max(float(col_w) - 9 * mm - 10, 16 * mm)
        bg_c = kpi_tone_bg[ti]
        bd_c = kpi_tone_border[ti]
        bar_c = kpi_tone_bar[ti]
        vhex = kpi_tone_val_hex[ti]
        lbl_para = Paragraph(
            f"<font color='#5c6578'>{_xml_escape(str(label))}</font>",
            st_kpi_lbl,
        )
        val_para = Paragraph(
            f"<font color='{vhex}'><b>{_xml_escape(str(value))}</b></font>",
            st_kpi_val,
        )
        txt = Table(
            [
                [lbl_para],
                [val_para],
            ],
            colWidths=[txt_col_w],
        )
        txt.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        row = Table([[icon_w, txt]], colWidths=[9 * mm, txt_col_w])
        row.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BACKGROUND", (0, 0), (-1, -1), bg_c),
                    ("BOX", (0, 0), (-1, -1), 0.4, bd_c),
                    ("ROUNDEDCORNERS", [16, 16, 16, 16]),
                    ("LINEBEFORE", (0, 0), (0, -1), 4, bar_c),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        return row

    def _impact_val_paragraph(lbl: str, val: str) -> Paragraph:
        tl = (lbl or "").lower()
        sv = str(val).strip()
        if sv in ("0", "0.0") and ("agotado" in tl or "bajo" in tl):
            return Paragraph("✓ Disponibilidad de Inventario", st_imp_val_ok)
        return Paragraph(_xml_escape(str(val)), st_imp_val)

    nk = [_reporte_norm_kpi_item(x) for x in kpis]
    kpi_n = len(nk)
    kpi_col_w = frame_w / max(kpi_n, 1)
    if kpi_n:
        kpi_row = [
            _kpi_cell(nk[i][0], nk[i][1], nk[i][2], kpi_col_w, i)
            for i in range(kpi_n)
        ]
        kpi_tbl = Table([kpi_row], colWidths=[kpi_col_w] * kpi_n)
    else:
        kpi_tbl = Table([[Paragraph("", muted)]], colWidths=[frame_w])
    _kpi_gap = 7
    _kpi_ts = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if kpi_n > 1:
        for ci in range(kpi_n - 1):
            _kpi_ts.append(("RIGHTPADDING", (ci, 0), (ci, 0), _kpi_gap))
    elif kpi_n == 1:
        _kpi_ts.append(("RIGHTPADDING", (0, 0), (0, 0), 0))
    kpi_tbl.setStyle(TableStyle(_kpi_ts))

    def _tabla(headers: list[str], rows: list[list[str]], _idx: int) -> Table:
        del _idx
        hdr_cells = [Paragraph(_xml_escape(str(h)), st_tbl_hdr) for h in headers]
        body_cells: list[list] = []
        for r in rows:
            row_cells = []
            for ci, cell in enumerate(r):
                hname = headers[ci] if ci < len(headers) else ""
                hn = (hname or "").strip().lower()
                if "nombre" in hn or "producto" in hn:
                    stc = st_tbl_cell_long
                elif _reporte_pdf_header_columna_derecha(hname):
                    stc = st_tbl_cell_r
                else:
                    stc = st_tbl_cell
                row_cells.append(Paragraph(_xml_escape(str(cell)), stc))
            body_cells.append(row_cells)
        data = [hdr_cells] + body_cells
        cw = _reporte_pdf_compute_col_widths(headers, total_mm=frame_w_mm)
        t = Table(data, colWidths=cw, repeatRows=1)
        c_line_tbl = colors.HexColor("#dddddd")
        ts = [
            ("ROUNDEDCORNERS", [10, 10, 10, 10]),
            ("BOX", (0, 0), (-1, -1), 0.45, c_line_tbl),
            ("BACKGROUND", (0, 0), (-1, 0), c_head_tbl),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 10),
            ("LINEBELOW", (0, 0), (-1, 0), 0.4, c_line_tbl),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, c_row_alt]),
            ("LINEBELOW", (0, 1), (-1, -2), 0.35, c_line_tbl),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ]
        t.setStyle(TableStyle(ts))
        return t

    elements: list = []
    elements.append(_BrandTopHairline())
    elements.append(Spacer(1, 3))
    elements.append(encabezado_tbl)
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Indicadores ejecutivos (KPIs)", st_kpi_h))
    elements.append(Spacer(1, 3))
    elements.append(kpi_tbl)

    g_specs = list(graficas or [])
    if g_specs:
        elements.append(Spacer(1, 20))
        elements.extend(
            _reporte_pdf_graficas_flowables(
                g_specs, h2_style=h2, muted_style=muted, frame_w_pt=frame_w, chart_scale=1.0
            )
        )

    elements.append(Paragraph("Detalle y tablas", h2))
    elements.append(Spacer(1, 10))

    for idx, (sec_title, headers, rows) in enumerate(secciones):
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(sec_title, h2))
        if not rows:
            elements.append(Paragraph("Sin datos en este período.", muted))
            continue
        elements.append(Spacer(1, 4))
        elements.append(_tabla(headers, rows, idx))

    cj = list(cajas_impacto or [])
    if cj:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("Resumen operativo", h2))
        elements.append(Spacer(1, 4))
        n_box = min(3, len(cj))
        box_cells: list = []
        for i in range(n_box):
            lbl, val = cj[i]
            inner_box = Table(
                [
                    [Paragraph(_xml_escape(str(lbl)), st_imp_lbl)],
                    [_impact_val_paragraph(str(lbl), str(val))],
                ],
                colWidths=[(frame_w / n_box) - 4 * mm],
            )
            inner_box.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f4f6")),
                        ("BOX", (0, 0), (-1, -1), 0.45, colors.HexColor("#e5e7eb")),
                        ("ROUNDEDCORNERS", [12, 12, 12, 12]),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ]
                )
            )
            box_cells.append(inner_box)
        col_w = frame_w / n_box
        impact_row = Table([box_cells], colWidths=[col_w] * n_box)
        impact_row.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        elements.append(impact_row)

    doc.build(elements)
    return buffer.getvalue()


def _reporte_dataset_from_request(request, tipo: str) -> dict:
    tipo = (tipo or "").strip().lower()
    if tipo not in {"productos", "usuarios", "ventas", "pagos"}:
        raise ValueError("Tipo de reporte no válido.")

    raw_desde, raw_hasta, fd, fh = _reporte_rango_default(request)
    rango_label = _reporte_rango_label(raw_desde, raw_hasta)

    if tipo == "productos":
        categoria = (request.GET.get("categoria") or "").strip()
        marca = (request.GET.get("marca") or "").strip()
        precio_min_raw = (request.GET.get("precioMin") or "").strip()
        precio_max_raw = (request.GET.get("precioMax") or "").strip()
        precio_min = _decimal_desde_post(precio_min_raw) if precio_min_raw else None
        precio_max = _decimal_desde_post(precio_max_raw) if precio_max_raw else None
        prod_f = _reporte_filtrar_productos(
            categoria=categoria, marca=marca, precio_min=precio_min, precio_max=precio_max
        )
        items = list(prod_f.select_related("proveedor")[:1000])
        n_total_filtro = prod_f.count()
        n_bajo_stock_f = prod_f.filter(activo=True, stock__gte=1, stock__lte=STOCK_BAJO_MAX).count()
        n_agotados_f = prod_f.filter(activo=True, stock=0).count()
        rows = [
            [
                str(p.id),
                p.codigo,
                p.nombre,
                p.categoria or "—",
                p.marca or "—",
                _cop(p.precio_venta if p.precio_venta is not None else p.costo_unitario),
                str(p.stock),
            ]
            for p in items
        ]

        total_sku = Producto.objects.filter(activo=True).count()
        valor_inv = (
            Producto.objects.filter(activo=True)
            .annotate(
                pu=Coalesce(
                    "precio_venta",
                    "costo_unitario",
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
            .aggregate(
                v=Sum(
                    F("stock") * F("pu"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )["v"]
            or Decimal("0")
        )

        ventas_rango = Venta.objects.filter(fecha_venta__gte=fd, fecha_venta__lte=fh).exclude(
            estado=Venta.Estado.ANULADA
        )
        n_pedidos_rango = ventas_rango.count()
        total_rango = ventas_rango.aggregate(s=Sum("total"))["s"] or Decimal("0")
        ticket_prom = (total_rango / n_pedidos_rango) if n_pedidos_rango else Decimal("0")

        top_vendidos = list(
            DetalleVenta.objects.filter(
                venta__fecha_venta__gte=fd,
                venta__fecha_venta__lte=fh,
                venta__estado__in=[Venta.Estado.ABIERTA, Venta.Estado.FACTURADA],
            )
            .values(
                "producto__id",
                "producto__nombre",
                "producto__precio_venta",
                "producto__costo_unitario",
            )
            .annotate(cantidad=Sum("cantidad"))
            .order_by("-cantidad")[:10]
        )
        top_rows = [[str(x["producto__id"]), x["producto__nombre"], str(x["cantidad"])] for x in top_vendidos]

        stock_critico = list(
            Producto.objects.filter(activo=True, stock__lte=_REPORTE_STOCK_ALERTA_CRITICO).order_by(
                "stock", "nombre"
            )[:50]
        )
        stock_crit_rows = [
            [str(p.id), p.nombre, p.categoria or "—", str(p.stock)] for p in stock_critico
        ]

        raw_cats = list(
            DetalleVenta.objects.filter(
                venta__fecha_venta__gte=fd,
                venta__fecha_venta__lte=fh,
                venta__estado__in=[Venta.Estado.ABIERTA, Venta.Estado.FACTURADA],
            )
            .values("producto__categoria")
            .annotate(
                monto=Sum(
                    F("cantidad") * F("precio_unitario"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                )
            )
        )
        cat_map: dict[str, Decimal] = {}
        for r in raw_cats:
            k = (r["producto__categoria"] or "").strip() or "Sin categoría"
            cat_map[k] = cat_map.get(k, Decimal("0")) + (r["monto"] or Decimal("0"))
        cat_sorted = sorted(cat_map.items(), key=lambda x: x[1], reverse=True)[:12]
        cat_labels = [a[0] for a in cat_sorted]
        cat_vals = [float(a[1]) for a in cat_sorted]

        cat_catalog_rows = list(
            prod_f.annotate(
                cn=Coalesce("categoria", Value("", output_field=CharField(max_length=120))),
            )
            .values("cn")
            .annotate(n=Count("id"))
            .order_by("-n")[:14]
        )
        dist_cat_lbl: list[str] = []
        dist_cat_val: list[float] = []
        for r in cat_catalog_rows:
            lab = (r["cn"] or "").strip() or "Sin categoría"
            dist_cat_lbl.append(lab)
            dist_cat_val.append(float(r["n"]))

        graficas_prod: list[dict] = []
        cat_dom_p = (categoria or "").strip()
        if not cat_dom_p:
            tc_auto = (
                Producto.objects.filter(activo=True)
                .exclude(categoria="")
                .values("categoria")
                .annotate(n=Count("id"))
                .order_by("-n")
                .first()
            )
            cat_dom_p = ((tc_auto or {}).get("categoria") or "").strip()
        if cat_dom_p:
            dm_lbl, dm_val, dm_tot = _reporte_dominio_marca_por_categoria(cat_dom_p)
            if dm_val and sum(dm_val) > 0:
                graficas_prod.append(
                    {
                        "titulo": "Dominio de marca por categoría",
                        "tipo": "rosca_dominio_marca",
                        "labels": dm_lbl,
                        "valores": dm_val,
                        "categoria_etiqueta": cat_dom_p,
                        "total_categoria": dm_tot,
                    }
                )
        top5_vol = _reporte_top5_productos_volumen(fd, fh)
        if top5_vol:
            graficas_prod.append(
                {
                    "titulo": "Top 5 productos más vendidos (volumen)",
                    "tipo": "radial_top5",
                    "items": [
                        {
                            "nombre": r["producto__nombre"] or "—",
                            "cantidad": int(r["cantidad"] or 0),
                            "precio_txt": _cop_decimales(
                                r["producto__precio_venta"]
                                if r["producto__precio_venta"] is not None
                                else (r["producto__costo_unitario"] or 0)
                            ),
                        }
                        for r in top5_vol
                    ],
                }
            )
        if dist_cat_val and sum(dist_cat_val) > 0:
            graficas_prod.append(
                {
                    "titulo": "Distribución por categoría (catálogo filtrado)",
                    "tipo": "pastel",
                    "labels": dist_cat_lbl,
                    "valores": dist_cat_val,
                }
            )
        if cat_vals and sum(cat_vals) > 0:
            graficas_prod.append(
                {
                    "titulo": "Ventas por categoría (COP)",
                    "tipo": "rosca",
                    "labels": cat_labels,
                    "valores": cat_vals,
                }
            )
        if len(cat_sorted) >= 2:
            c5 = cat_sorted[:5]
            graficas_prod.append(
                {
                    "titulo": "Ranking categorías por facturación (COP)",
                    "tipo": "barras_horizontales",
                    "labels": [a[0] for a in c5],
                    "valores": [float(a[1]) for a in c5],
                }
            )

        return {
            "titulo": "Reporte de Productos",
            "headers": ["ID", "Código", "Nombre", "Categoría", "Marca", "Precio", "Stock"],
            "rows": rows,
            "filtros": [
                rango_label,
                f"Categoría: {categoria or 'Todas'}",
                f"Marca: {marca or 'Todas'}",
                f"Dominio marca (categoría base): {categoria or (f'{cat_dom_p} (auto)' if cat_dom_p else '—')}",
                f"Precio min: {precio_min_raw or '—'}",
                f"Precio max: {precio_max_raw or '—'}",
                f"Total registros: {len(rows)}",
            ],
            "pdf_v2": {
                "subtitulo": "Business Intelligence — Catálogo",
                "rango": rango_label,
                "cajas_impacto": [
                    ("Total (catálogo filtrado)", str(n_total_filtro)),
                    ("Bajo stock", str(n_bajo_stock_f)),
                    ("Agotados", str(n_agotados_f)),
                ],
                "kpis": [
                    ("Total SKU", str(total_sku), "sku"),
                    ("Valor total inventario", _cop(valor_inv), "money"),
                    ("Ticket promedio (rango)", _cop(ticket_prom), "ticket"),
                ],
                "graficas": graficas_prod,
                "secciones": [
                    ("Top 10 productos más vendidos", ["ID", "Producto", "Unidades"], top_rows),
                    (
                        f"Alerta — stock crítico (≤{_REPORTE_STOCK_ALERTA_CRITICO} u.)",
                        ["ID", "Producto", "Categoría", "Stock"],
                        stock_crit_rows,
                    ),
                    (
                        "Muestra de catálogo (filtros)",
                        ["ID", "Código", "Nombre", "Categoría", "Marca", "Precio", "Stock"],
                        rows[:60],
                    ),
                ],
            },
        }

    if tipo == "usuarios":
        rol = (request.GET.get("rol") or "").strip().lower()
        busqueda = (request.GET.get("busqueda") or "").strip()
        items = list(_reporte_filtrar_usuarios(rol=rol, busqueda=busqueda)[:1000])
        rows = [
            [
                str(u.id),
                f"{u.nombres} {u.apellidos}".strip(),
                u.correo_electronico,
                u.get_rol_display(),
                "Activo" if u.activo else "Inactivo",
                f"{u.tipo_documento} {u.numero_documento}",
            ]
            for u in items
        ]

        hoy = timezone.localdate()
        total_u = Usuario.objects.count()
        activos = Usuario.objects.filter(activo=True).count()
        nuevos_mes = Usuario.objects.filter(creado_en__year=hoy.year, creado_en__month=hoy.month).count()

        end_m = fh.replace(day=1)
        line_labels: list[str] = []
        line_vals: list[float] = []
        for k in range(11, -1, -1):
            ref = _reporte_add_months(end_m, -k)
            y, mo = ref.year, ref.month
            line_labels.append(f"{_MESES_CORTO[mo - 1]} {str(y)[2:]}")
            fd_m = date(y, mo, 1)
            fh_m = date(y, mo, monthrange(y, mo)[1])
            line_vals.append(
                float(Usuario.objects.filter(creado_en__date__gte=fd_m, creado_en__date__lte=fh_m).count())
            )

        role_rows = list(Usuario.objects.values("rol").annotate(n=Count("id")))
        role_lbl = dict(Usuario.Rol.choices)
        pie_labels = [str(role_lbl.get(r["rol"], r["rol"])) for r in role_rows]
        pie_vals = [float(r["n"]) for r in role_rows]

        top_gasto: list = []
        top_gasto_rows: list[list[str]] = []
        if fd and fh:
            top_gasto = list(
                Venta.objects.filter(fecha_venta__gte=fd, fecha_venta__lte=fh)
                .exclude(estado=Venta.Estado.ANULADA)
                .values("usuario__id", "usuario__nombres", "usuario__apellidos", "usuario__correo_electronico")
                .annotate(total=Sum("total"), pedidos=Count("id"))
                .order_by("-total")[:10]
            )
            top_gasto_rows = [
                [
                    str(x["usuario__id"]),
                    f'{(x["usuario__nombres"] or "").strip()} {(x["usuario__apellidos"] or "").strip()}'.strip(),
                    x["usuario__correo_electronico"] or "—",
                    str(x["pedidos"]),
                    _cop(x["total"]),
                ]
                for x in top_gasto
            ]

        graficas_usu: list[dict] = []
        graficas_usu.append(
            {
                "titulo": "Crecimiento — nuevos usuarios por mes",
                "tipo": "lineas",
                "labels": line_labels,
                "valores": line_vals,
            }
        )
        if pie_vals and sum(pie_vals) > 0:
            graficas_usu.append(
                {
                    "titulo": "Distribución por rol",
                    "tipo": "pastel",
                    "labels": pie_labels,
                    "valores": pie_vals,
                }
            )
        if top_gasto:
            tg5 = top_gasto[:5]
            graficas_usu.append(
                {
                    "titulo": "Top clientes por gasto en el período (COP)",
                    "tipo": "barras_horizontales",
                    "labels": [
                        _reporte_label_corta(
                            f'{(x["usuario__nombres"] or "").strip()} {(x["usuario__apellidos"] or "").strip()}'.strip()
                            or "—",
                            20,
                        )
                        for x in tg5
                    ],
                    "valores": [float(x["total"] or 0) for x in tg5],
                }
            )

        return {
            "titulo": "Reporte de Usuarios",
            "headers": ["ID", "Nombre", "Correo", "Rol", "Estado", "Documento"],
            "rows": rows,
            "filtros": [
                rango_label,
                f"Rol: {rol or 'Todos'}",
                f"Búsqueda: {busqueda or '—'}",
                f"Total registros: {len(rows)}",
            ],
            "pdf_v2": {
                "subtitulo": "Business Intelligence — Usuarios",
                "rango": rango_label,
                "kpis": [
                    ("Total usuarios", str(total_u), "users"),
                    ("Usuarios activos", str(activos), "check"),
                    ("Nuevos (este mes)", str(nuevos_mes), "clock"),
                ],
                "graficas": graficas_usu,
                "secciones": [
                    (
                        "Top 10 clientes con mayor gasto",
                        ["ID", "Cliente", "Correo", "Pedidos", "Total (COP)"],
                        top_gasto_rows,
                    ),
                    ("Listado (filtros)", ["ID", "Nombre", "Correo", "Rol", "Estado", "Documento"], rows[:100]),
                ],
            },
        }

    if tipo == "pagos":
        estado_pago = (request.GET.get("estadoPago") or "").strip().lower()
        qs = Pago.objects.all().order_by("-fecha_pago", "-id")
        if fd:
            qs = qs.filter(fecha_pago__gte=fd)
        if fh:
            qs = qs.filter(fecha_pago__lte=fh)
        if estado_pago in {
            Pago.EstadoPago.PENDIENTE,
            Pago.EstadoPago.APROBADO,
            Pago.EstadoPago.RECHAZADO,
            Pago.EstadoPago.REEMBOLSADO,
        }:
            qs = qs.filter(estado_pago=estado_pago)
        pagos = list(qs[:1000])
        rows = [
            [
                str(p.id),
                p.numero_factura,
                str(p.fecha_pago),
                p.get_estado_pago_display(),
                _cop(p.monto),
            ]
            for p in pagos
        ]

        recaudado = qs.filter(estado_pago=Pago.EstadoPago.APROBADO).aggregate(s=Sum("monto"))["s"] or Decimal("0")
        ok = qs.filter(estado_pago=Pago.EstadoPago.APROBADO).count()
        fail = qs.filter(estado_pago=Pago.EstadoPago.RECHAZADO).count()
        line_sub = ExpressionWrapper(
            F("detalle_venta__cantidad") * F("detalle_venta__precio_unitario"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        metodos = list(
            MedioPago.objects.filter(pago__in=qs)
            .values("metodo_pago")
            .annotate(pagos_distintos=Count("pago_id", distinct=True))
            .order_by("-pagos_distintos")
        )
        metodos_rows = [[_metodo_pago_label(m["metodo_pago"]), str(m["pagos_distintos"])] for m in metodos]
        monto_por_metodo = list(
            MedioPago.objects.filter(pago__in=qs)
            .annotate(line_sub=line_sub)
            .values("metodo_pago")
            .annotate(total=Sum("line_sub"))
            .order_by("-total")
        )
        monto_met_rows = [[_metodo_pago_label(m["metodo_pago"]), _cop(m["total"])] for m in monto_por_metodo]

        metodos_pie = list(
            MedioPago.objects.filter(pago__in=qs)
            .values("metodo_pago")
            .annotate(n=Count("pago_id", distinct=True))
            .order_by("-n")[:10]
        )

        graficas_pg: list[dict] = []
        daily_pg = list(
            qs.annotate(d=TruncDay("fecha_pago")).values("d").annotate(n=Count("id")).order_by("d")[:60]
        )
        if daily_pg:
            graficas_pg.append(
                {
                    "titulo": "Volumen de pagos por día (cantidad)",
                    "tipo": "lineas",
                    "labels": [x["d"].strftime("%d/%m") if x.get("d") else "—" for x in daily_pg],
                    "valores": [float(x["n"]) for x in daily_pg],
                }
            )
        if metodos_pie:
            graficas_pg.append(
                {
                    "titulo": "Métodos de pago más usados",
                    "tipo": "pastel",
                    "labels": [_metodo_pago_label(x["metodo_pago"]) for x in metodos_pie],
                    "valores": [float(x["n"]) for x in metodos_pie],
                }
            )
        estados_pg = list(qs.values("estado_pago").annotate(n=Count("id")).order_by("-n"))
        lbl_ep = dict(Pago.EstadoPago.choices)
        if estados_pg:
            graficas_pg.append(
                {
                    "titulo": "Pagos por estado (flujo operativo)",
                    "tipo": "rosca",
                    "labels": [str(lbl_ep.get(x["estado_pago"], x["estado_pago"])) for x in estados_pg],
                    "valores": [float(x["n"]) for x in estados_pg],
                }
            )
        if monto_por_metodo:
            mm6 = monto_por_metodo[:6]
            graficas_pg.append(
                {
                    "titulo": "Monto acumulado por método de pago (COP)",
                    "tipo": "barras",
                    "labels": [_metodo_pago_label(x["metodo_pago"]) for x in mm6],
                    "valores": [float(x["total"] or 0) for x in mm6],
                }
            )

        pendientes = list(qs.filter(estado_pago=Pago.EstadoPago.PENDIENTE).order_by("-fecha_pago", "-id")[:40])
        pend_rows = [
            [str(p.id), p.numero_factura, str(p.fecha_pago), _cop(p.monto)] for p in pendientes
        ]

        return {
            "titulo": "Reporte de Pagos",
            "headers": ["ID", "Factura", "Fecha pago", "Estado", "Monto (COP)"],
            "rows": rows,
            "filtros": [
                rango_label,
                f"Estado: {estado_pago or 'Todos'}",
                f"Total registros: {len(rows)}",
            ],
            "pdf_v2": {
                "subtitulo": "Business Intelligence — Pagos",
                "rango": rango_label,
                "kpis": [
                    ("Total recaudado (aprobad.)", _cop(recaudado), "money"),
                    ("Pagos exitosos", str(ok), "check"),
                    ("Pagos fallidos", str(fail), "fail"),
                ],
                "graficas": graficas_pg,
                "secciones": [
                    (
                        "Pagos pendientes por confirmar",
                        ["ID", "Factura", "Fecha pago", "Monto (COP)"],
                        pend_rows,
                    ),
                    ("Métodos de pago más usados", ["Método", "Cantidad"], metodos_rows),
                    ("Monto total por método (líneas)", ["Método", "Monto (COP)"], monto_met_rows),
                    ("Listado de pagos (muestra)", ["ID", "Factura", "Fecha pago", "Estado", "Monto (COP)"], rows[:100]),
                ],
            },
        }

    # Ventas — BI v2
    estado = (request.GET.get("estado") or "").strip().lower()
    qv = _reporte_filtrar_ventas(estado=estado, fecha_desde=raw_desde, fecha_hasta=raw_hasta)
    qv_na = qv.exclude(estado=Venta.Estado.ANULADA)
    ag = qv_na.aggregate(s=Sum("total"), n=Count("id"))
    total_ventas = ag["s"] or Decimal("0")
    pedidos = int(ag["n"] or 0)
    ticket = (total_ventas / pedidos) if pedidos else Decimal("0")

    items = list(qv[:1000])
    rows = [
        [
            str(v.id),
            f"{v.usuario.nombres} {v.usuario.apellidos}".strip() if v.usuario_id else "—",
            str(v.fecha_venta),
            v.get_estado_display(),
            _cop(v.total),
        ]
        for v in items
    ]

    categoria_ventas = (request.GET.get("categoria") or "").strip()
    cat_dom_v = categoria_ventas
    if not cat_dom_v and fd and fh:
        cat_dom_v = _reporte_top_categoria_ventas(fd, fh)

    graficas_v: list[dict] = []
    top5_v = _reporte_top5_productos_volumen(fd, fh) if fd and fh else []
    if top5_v:
        graficas_v.append(
            {
                "titulo": "Top 5 productos más vendidos (volumen)",
                "tipo": "radial_top5",
                "items": [
                    {
                        "nombre": r["producto__nombre"] or "—",
                        "cantidad": int(r["cantidad"] or 0),
                        "precio_txt": _cop_decimales(
                            r["producto__precio_venta"]
                            if r["producto__precio_venta"] is not None
                            else (r["producto__costo_unitario"] or 0)
                        ),
                    }
                    for r in top5_v
                ],
            }
        )
    if cat_dom_v:
        dvl, dvv, dvt = _reporte_dominio_marca_por_categoria(cat_dom_v)
        if dvv and sum(dvv) > 0:
            graficas_v.append(
                {
                    "titulo": "Dominio de marca por categoría",
                    "tipo": "rosca_dominio_marca",
                    "labels": dvl,
                    "valores": dvv,
                    "categoria_etiqueta": cat_dom_v,
                    "total_categoria": dvt,
                }
            )

    if fd and fh:
        end_m = fh.replace(day=1)
        yoy_labels: list[str] = []
        cur_serie: list[float] = []
        prev_serie: list[float] = []
        for k in range(11, -1, -1):
            ref = _reporte_add_months(end_m, -k)
            y, mo = ref.year, ref.month
            yoy_labels.append(f"{_MESES_CORTO[mo - 1]} {str(y)[2:]}")
            fd_c = date(y, mo, 1)
            fh_c = date(y, mo, monthrange(y, mo)[1])
            cur_serie.append(
                float(
                    Venta.objects.filter(fecha_venta__gte=fd_c, fecha_venta__lte=fh_c)
                    .exclude(estado=Venta.Estado.ANULADA)
                    .aggregate(s=Sum("total"))["s"]
                    or 0
                )
            )
            py, pm = y - 1, mo
            fd_p = date(py, pm, 1)
            fh_p = date(py, pm, monthrange(py, pm)[1])
            prev_serie.append(
                float(
                    Venta.objects.filter(fecha_venta__gte=fd_p, fecha_venta__lte=fh_p)
                    .exclude(estado=Venta.Estado.ANULADA)
                    .aggregate(s=Sum("total"))["s"]
                    or 0
                )
            )
        graficas_v.append(
            {
                "titulo": "Ingresos mensuales vs año anterior (COP)",
                "tipo": "lineas_area_multiserie",
                "labels": yoy_labels,
                "series": [
                    {"label": "Año actual", "valores": cur_serie},
                    {"label": "Año anterior", "valores": prev_serie},
                ],
            }
        )

        est_pairs = list(
            Venta.objects.filter(
                fecha_venta__gte=fd,
                fecha_venta__lte=fh,
                estado__in=[Venta.Estado.ABIERTA, Venta.Estado.FACTURADA],
            )
            .values("estado")
            .annotate(n=Count("id"))
        )
        est_lbl = dict(Venta.Estado.choices)
        donut_lbl = [str(est_lbl.get(x["estado"], x["estado"])) for x in est_pairs]
        donut_vals = [float(x["n"]) for x in est_pairs]
        if donut_vals and sum(donut_vals) > 0:
            graficas_v.append(
                {
                    "titulo": "Ventas por estado (Abierta / Facturada)",
                    "tipo": "rosca",
                    "labels": donut_lbl,
                    "valores": donut_vals,
                }
            )

        labd: list[str] = []
        valsd: list[float] = []
        for i in range(13, -1, -1):
            d0 = fh - timedelta(days=i)
            if fd and d0 < fd:
                continue
            labd.append(d0.strftime("%d/%m"))
            valsd.append(
                float(
                    Venta.objects.filter(fecha_venta=d0)
                    .exclude(estado=Venta.Estado.ANULADA)
                    .aggregate(s=Sum("total"))["s"]
                    or 0
                )
            )
        if labd:
            graficas_v.append(
                {
                    "titulo": "Ingresos diarios — ventana móvil 14 días (COP)",
                    "tipo": "lineas",
                    "labels": labd,
                    "valores": valsd,
                }
            )

    ultimas = list(qv.order_by("-fecha_venta", "-id")[:20])
    ultimas_rows = [
        [
            str(v.id),
            f"{v.usuario.nombres} {v.usuario.apellidos}".strip() if v.usuario_id else "—",
            str(v.fecha_venta),
            v.get_estado_display(),
            _cop(v.total),
        ]
        for v in ultimas
    ]

    _hero_im = next(
        (i for i, g in enumerate(graficas_v) if "Ingresos mensuales" in (g.get("titulo") or "")),
        None,
    )
    if _hero_im is not None and _hero_im > 0:
        _g = graficas_v.pop(_hero_im)
        graficas_v.insert(0, _g)

    return {
        "titulo": "Reporte de Ventas",
        "headers": ["ID", "Cliente", "Fecha", "Estado", "Total (COP)"],
        "rows": rows,
        "filtros": [
            rango_label,
            f"Estado: {estado or 'Todos'}",
            f"Categoría (dominio marca): {categoria_ventas or (f'Automática ({cat_dom_v})' if cat_dom_v else '—')}",
            f"Total registros: {len(rows)}",
        ],
        "pdf_v2": {
            "subtitulo": "Business Intelligence — Ventas",
            "rango": rango_label,
            "kpis": [
                ("Total ingresos (COP)", _cop(total_ventas), "money"),
                ("Total ventas", str(pedidos), "chart"),
                ("Ticket promedio (COP)", _cop(ticket), "ticket"),
            ],
            "graficas": graficas_v,
            "secciones": [
                ("Últimas 20 ventas realizadas", ["ID", "Cliente", "Fecha", "Estado", "Total (COP)"], ultimas_rows),
                (
                    "Listado filtrado (muestra)",
                    ["ID", "Cliente", "Fecha", "Estado", "Total (COP)"],
                    rows[:80],
                ),
            ],
        },
    }


@_admin_login_required
def admin_reportes(request):
    usuario = _admin_usuario_sesion(request)

    tipo = (request.GET.get("tipo") or "productos").strip().lower()
    if tipo not in {"productos", "usuarios", "ventas", "pagos"}:
        tipo = "productos"

    categoria = (request.GET.get("categoria") or "").strip()
    marca = (request.GET.get("marca") or "").strip()
    precio_min_raw = (request.GET.get("precioMin") or "").strip()
    precio_max_raw = (request.GET.get("precioMax") or "").strip()
    rol = (request.GET.get("rol") or "").strip().lower()
    busqueda = (request.GET.get("busqueda") or "").strip()
    estado = (request.GET.get("estado") or "").strip().lower()
    estado_pago = (request.GET.get("estadoPago") or "").strip().lower()
    fecha_desde, fecha_hasta, fd, fh = _reporte_rango_default(request)

    precio_min = _decimal_desde_post(precio_min_raw) if precio_min_raw else None
    precio_max = _decimal_desde_post(precio_max_raw) if precio_max_raw else None

    productos_qs = _reporte_filtrar_productos(
        categoria=categoria,
        marca=marca,
        precio_min=precio_min,
        precio_max=precio_max,
    )
    usuarios_qs = _reporte_filtrar_usuarios(rol=rol, busqueda=busqueda)
    ventas_qs = _reporte_filtrar_ventas(estado=estado, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)
    pagos_qs = Pago.objects.all().order_by("-fecha_pago", "-id")
    if fd:
        pagos_qs = pagos_qs.filter(fecha_pago__gte=fd)
    if fh:
        pagos_qs = pagos_qs.filter(fecha_pago__lte=fh)
    if estado_pago in {
        Pago.EstadoPago.PENDIENTE,
        Pago.EstadoPago.APROBADO,
        Pago.EstadoPago.RECHAZADO,
        Pago.EstadoPago.REEMBOLSADO,
    }:
        pagos_qs = pagos_qs.filter(estado_pago=estado_pago)

    usuarios_por_rol = {
        "admin": Usuario.objects.filter(rol=Usuario.Rol.ADMIN).count(),
        "empleado": Usuario.objects.filter(rol=Usuario.Rol.EMPLEADO).count(),
        "cliente": Usuario.objects.filter(rol=Usuario.Rol.CLIENTE).count(),
    }
    productos_por_categoria = (
        Producto.objects.exclude(categoria="")
        .values("categoria")
        .annotate(total=Count("id"))
        .order_by("-total", "categoria")[:8]
    )

    hoy = timezone.localdate()
    ventas_por_mes = []
    for i in range(5, -1, -1):
        ref = hoy.replace(day=1) - timedelta(days=31 * i)
        total_mes = (
            Venta.objects.filter(fecha_venta__year=ref.year, fecha_venta__month=ref.month).aggregate(s=Sum("total"))[
                "s"
            ]
            or Decimal("0")
        )
        ventas_por_mes.append({"mes": ref.strftime("%b %Y"), "total": total_mes})

    # —— Dashboard: línea 12 meses + rosca categorías + tablas compactas ——
    dash_line_labels: list[str] = []
    dash_line_values: list[float] = []
    end_m_dash = hoy.replace(day=1)
    for k in range(11, -1, -1):
        ref_m = _reporte_add_months(end_m_dash, -k)
        y_m, mo_m = ref_m.year, ref_m.month
        dash_line_labels.append(f"{_MESES_CORTO[mo_m - 1]} '{str(y_m)[2:]}")
        tot_m = (
            Venta.objects.filter(fecha_venta__year=y_m, fecha_venta__month=mo_m)
            .exclude(estado=Venta.Estado.ANULADA)
            .aggregate(s=Sum("total"))["s"]
            or Decimal("0")
        )
        dash_line_values.append(float(tot_m))
    dpc_list = list(productos_por_categoria)
    if dpc_list:
        dash_donut_labels = [str(x["categoria"]) for x in dpc_list]
        dash_donut_values = [float(x["total"]) for x in dpc_list]
    else:
        n_sin = Producto.objects.filter(categoria="").count()
        n_tot = Producto.objects.count()
        dash_donut_labels = ["Sin categoría"] if n_sin else ["Catálogo"]
        dash_donut_values = [float(n_sin or n_tot or 1)]

    top5_dashboard = list(
        DetalleVenta.objects.filter(
            venta__fecha_venta__gte=fd,
            venta__fecha_venta__lte=fh,
            venta__estado__in=[Venta.Estado.ABIERTA, Venta.Estado.FACTURADA],
        )
        .values("producto__nombre")
        .annotate(cantidad=Sum("cantidad"))
        .order_by("-cantidad")[:5]
    )
    stock_critico_dashboard = list(
        Producto.objects.filter(activo=True, stock__lte=_REPORTE_STOCK_ALERTA_CRITICO).order_by(
            "stock", "nombre"
        )[:5]
    )

    _rq: dict[str, str] = {"fechaDesde": fecha_desde, "fechaHasta": fecha_hasta}
    if tipo == "productos":
        if categoria:
            _rq["categoria"] = categoria
        if marca:
            _rq["marca"] = marca
        if precio_min_raw:
            _rq["precioMin"] = precio_min_raw
        if precio_max_raw:
            _rq["precioMax"] = precio_max_raw
    elif tipo == "usuarios":
        if rol:
            _rq["rol"] = rol
        if busqueda:
            _rq["busqueda"] = busqueda
    elif tipo == "ventas":
        if estado:
            _rq["estado"] = estado
        if categoria:
            _rq["categoria"] = categoria
    elif tipo == "pagos" and estado_pago:
        _rq["estadoPago"] = estado_pago
    reportes_action_query = urllib_parse.urlencode(_rq)

    ctx = {
        "usuario": usuario,
        "tipo": tipo,
        "categoria": categoria,
        "marca": marca,
        "precio_min": precio_min_raw,
        "precio_max": precio_max_raw,
        "rol": rol,
        "busqueda": busqueda,
        "estado": estado,
        "estado_pago": estado_pago,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "productos_count": Producto.objects.count(),
        "usuarios_count": Usuario.objects.count(),
        "ventas_count": Venta.objects.count(),
        "pagos_count": Pago.objects.count(),
        "monto_ventas_total": Venta.objects.aggregate(s=Sum("total"))["s"] or Decimal("0"),
        "categorias": sorted(
            set(Producto.objects.exclude(categoria="").values_list("categoria", flat=True).distinct()), key=str.lower
        ),
        "marcas": sorted(
            set(Producto.objects.exclude(marca="").values_list("marca", flat=True).distinct()), key=str.lower
        ),
        "usuarios_por_rol": usuarios_por_rol,
        "productos_por_categoria": list(productos_por_categoria),
        "ventas_por_mes": ventas_por_mes,
        "preview_productos": list(productos_qs[:15]),
        "preview_usuarios": list(usuarios_qs[:15]),
        "preview_ventas": list(ventas_qs[:15]),
        "preview_pagos": list(pagos_qs[:15]),
        "dash_charts_dict": {
            "line": {"labels": dash_line_labels, "data": dash_line_values},
            "donut": {"labels": dash_donut_labels, "data": dash_donut_values},
        },
        "top5_dashboard": top5_dashboard,
        "stock_critico_dashboard": stock_critico_dashboard,
        "reportes_action_query": reportes_action_query,
    }
    return render(request, "frontend/admin/reportes.html", ctx)


@_admin_login_required
def admin_reportes_preview(request, tipo: str):
    _admin_usuario_sesion(request)
    try:
        data = _reporte_dataset_from_request(request, tipo)
    except ValueError:
        messages.error(request, "Tipo de reporte no válido.")
        return redirect("web_admin_reportes")
    pdf_v2 = data.get("pdf_v2") or {}
    kpi_items = [_reporte_norm_kpi_item(x) for x in (pdf_v2.get("kpis") or [])]
    charts_json = json.dumps(pdf_v2.get("graficas") or [], ensure_ascii=False)
    return render(
        request,
        "frontend/admin/reportes_preview.html",
        {
            "tipo": tipo,
            "titulo": data["titulo"],
            "headers": data["headers"],
            "rows": data["rows"],
            "filtros": data["filtros"],
            "pdf_v2": pdf_v2,
            "kpi_items": kpi_items,
            "charts_json": charts_json,
        },
    )


@_admin_login_required
def admin_reportes_pdf(request, tipo: str):
    usuario = _admin_usuario_sesion(request)
    tipo = (tipo or "").strip().lower()
    if tipo not in {"productos", "usuarios", "ventas", "pagos"}:
        messages.error(request, "Tipo de reporte no válido.")
        return redirect("web_admin_reportes")

    generado_por = f"{usuario.nombres} {usuario.apellidos}".strip() or usuario.correo_electronico

    try:
        data = _reporte_dataset_from_request(request, tipo)
        v2 = data.get("pdf_v2") or {}
        pdf = _reporte_build_pdf_v2(
            titulo=data["titulo"],
            subtitulo=str(v2.get("subtitulo") or "Sistema de Gestión"),
            rango=str(v2.get("rango") or ""),
            kpis=list(v2.get("kpis") or []),
            secciones=list(v2.get("secciones") or []),
            graficas=list(v2.get("graficas") or []),
            generado_por=generado_por,
            cajas_impacto=list(v2.get("cajas_impacto") or []),
        )
    except RuntimeError:
        messages.error(
            request,
            "Falta la dependencia para PDF. Instala reportlab en tu entorno virtual: pip install reportlab",
        )
        return redirect("web_admin_reportes")

    filename = f"reporte_{tipo}_{timezone.localtime().strftime('%Y%m%d_%H%M%S')}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    try:
        from web.reporte_pdf_graficas import REPORTE_PDF_GRAFICAS_BUILD

        response["X-TechNova-Pdf-Graficas"] = REPORTE_PDF_GRAFICAS_BUILD
    except Exception:  # noqa: BLE001
        pass
    return response


@_cliente_login_required
def perfil_cliente(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = None
    if uid:
        try:
            usuario = Usuario.objects.get(pk=uid)
        except Usuario.DoesNotExist:
            usuario = None
    favoritos_count = Favorito.objects.filter(usuario_id=uid).count() if uid else 0
    carrito_count = len(get_carrito_lineas_service().listar_items(uid)) if uid else 0
    pedidos_count = Venta.objects.filter(usuario_id=uid).count() if uid else 0
    compras_count = pedidos_count
    medios_pago_count = MetodoPagoUsuario.objects.filter(usuario_id=uid).count() if uid else 0

    notificaciones_count = 0
    if uid:
        ventas_ids = list(
            Venta.objects.filter(usuario_id=uid).order_by("-fecha_venta", "-id").values_list("id", flat=True)[:40]
        )
        if ventas_ids:
            notificaciones_count += len(ventas_ids)
            notificaciones_count += (
                Pago.objects.filter(medios_pago__detalle_venta__venta_id__in=ventas_ids)
                .distinct()
                .count()
            )
            notificaciones_count += (
                Envio.objects.filter(venta_id__in=ventas_ids, activo=True)
                .values("venta_id")
                .distinct()
                .count()
            )
        nuevos_productos_count = Producto.objects.filter(activo=True).count()
        notificaciones_count += min(nuevos_productos_count, 12)

    ctx = {
        "usuario": usuario,
        "favoritos_count": favoritos_count,
        "carrito_count": carrito_count,
        "pedidos_count": pedidos_count,
        "notificaciones_count": notificaciones_count,
        "medios_pago_count": medios_pago_count,
        "compras_count": compras_count,
    }
    return render(request, "frontend/cliente/perfil.html", ctx)


@_cliente_login_required
def perfil_editar(request):
    """Equivalente a GET/POST /perfil/edit del Java (teléfono, dirección + contraseña actual)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    try:
        usuario = Usuario.objects.get(pk=uid) if uid else None
    except Usuario.DoesNotExist:
        usuario = None
    if not usuario:
        messages.error(request, "Usuario no encontrado.")
        return redirect("web_cliente_perfil")

    if request.method == "POST":
        telefono = (request.POST.get("telefono") or "").strip()
        direccion = (request.POST.get("direccion") or "").strip()
        current_password = request.POST.get("current_password") or ""
        if not credenciales_coinciden(current_password, usuario.contrasena_hash):
            messages.error(request, "La contraseña actual no es correcta.")
            return redirect("web_cliente_perfil_editar")
        cambios = []
        if usuario.telefono != telefono:
            cambios.append("teléfono")
        if usuario.direccion != direccion:
            cambios.append("dirección")
        usuario.telefono = telefono
        usuario.direccion = direccion
        usuario.save(update_fields=["telefono", "direccion", "actualizado_en"])
        if cambios:
            from mensajeria.services.notificaciones_admin import notificar_usuario_actualizado

            notificar_usuario_actualizado(
                usuario_id=usuario.id,
                correo=usuario.correo_electronico,
                cambios=cambios,
                origen="cliente_perfil",
            )
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect("web_cliente_perfil")

    return render(request, "frontend/cliente/perfil_editar.html", {"usuario": usuario})


@require_http_methods(["POST"])
def perfil_desactivar(request):
    """Equivalente a POST /cliente/perfil/desactivar del Java (JSON)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return JsonResponse({"success": False, "message": "No autenticado."}, status=401)
    try:
        usuario = Usuario.objects.get(pk=uid)
        usuario.activo = False
        usuario.save(update_fields=["activo", "actualizado_en"])
    except Usuario.DoesNotExist:
        return JsonResponse({"success": False, "message": "Usuario no encontrado."}, status=404)
    request.session.flush()
    return JsonResponse({"success": True, "message": "Cuenta desactivada."})


@_cliente_login_required
def favoritos_page(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    favoritos = Favorito.objects.select_related("producto").filter(usuario_id=uid).order_by("-id")
    productos = []
    for f in favoritos:
        p = f.producto
        productos.append(
            {
                "id": p.id,
                "nombre": p.nombre,
                "imagen": p.imagen_url or "",
                "precio": p.precio_venta,
            }
        )
    return render(request, "frontend/cliente/favoritos.html", {"productos": productos})


@_cliente_login_required
@require_POST
def favorito_quitar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    wants_json = _wants_json_response(request)
    try:
        producto_id = int(request.POST.get("producto_id", 0))
    except (TypeError, ValueError):
        if wants_json:
            return JsonResponse({"ok": False, "message": "Producto no válido."}, status=400)
        messages.error(request, "Producto no válido.")
        return redirect("web_favoritos")
    if get_carrito_query_service().eliminar_favorito(uid, producto_id):
        if wants_json:
            return JsonResponse({"ok": True, "message": "Producto quitado de favoritos."})
        messages.success(request, "Producto quitado de favoritos.")
    else:
        if wants_json:
            return JsonResponse({"ok": False, "message": "No se encontró ese favorito."}, status=404)
        messages.warning(request, "No se encontró ese favorito.")
    return redirect("web_favoritos")


@_cliente_login_required
@require_POST
def favorito_agregar_carrito(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    wants_json = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or (request.headers.get("Accept") or "").startswith("application/json")
        or (request.content_type or "").startswith("application/json")
    )
    producto_id = None
    try:
        if (request.content_type or "").startswith("application/json") and request.body:
            payload = json.loads(request.body.decode())
            producto_id = int(payload.get("producto_id"))
        else:
            producto_id = int(request.POST.get("producto_id", 0))
    except (TypeError, ValueError, json.JSONDecodeError):
        if wants_json:
            return JsonResponse({"ok": False, "message": "Producto no válido."}, status=400)
        messages.error(request, "Producto no válido.")
        return redirect("web_favoritos")
    try:
        get_carrito_lineas_service().agregar_producto(uid, producto_id, 1)
        if wants_json:
            return JsonResponse({"ok": True, "message": "Producto agregado al carrito."})
        messages.success(request, "Producto agregado al carrito.")
    except ValueError as exc:
        if wants_json:
            return JsonResponse({"ok": False, "message": str(exc)}, status=400)
        messages.error(request, str(exc))
    return redirect("web_favoritos")


@_cliente_login_required
def notificaciones_cliente(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    notificaciones: list[dict] = []

    ventas = list(
        Venta.objects.filter(usuario_id=uid)
        .order_by("-fecha_venta", "-id")[:40]
    )
    for venta in ventas:
        notificaciones.append(
            {
                "tipo": "compra",
                "titulo": f"Compra registrada #{venta.id}",
                "detalle": f"Tu compra fue creada el {venta.fecha_venta.strftime('%d/%m/%Y')}.",
                "fecha": venta.fecha_venta,
                "estado": (venta.estado or "").replace("_", " ").title(),
            }
        )

        pago = (
            Pago.objects.filter(medios_pago__detalle_venta__venta_id=venta.id)
            .distinct()
            .order_by("-fecha_pago", "-id")
            .first()
        )
        if pago:
            notificaciones.append(
                {
                    "tipo": "pago",
                    "titulo": f"Estado de pago de compra #{venta.id}",
                    "detalle": f"Factura: {pago.numero_factura}.",
                    "fecha": pago.fecha_pago,
                    "estado": (pago.estado_pago or "").replace("_", " ").title(),
                }
            )

        envio = (
            Envio.objects.filter(venta_id=venta.id, activo=True)
            .select_related("transportadora")
            .order_by("-fecha_envio", "-id")
            .first()
        )
        if envio:
            notificaciones.append(
                {
                    "tipo": "pedido",
                    "titulo": f"Estado del pedido #{venta.id}",
                    "detalle": f"Transportadora: {envio.transportadora.nombre}. Guía: {envio.numero_guia}.",
                    "fecha": envio.fecha_envio.date(),
                    "estado": (envio.estado or "").replace("_", " ").title(),
                }
            )

    nuevos_productos = list(
        Producto.objects.filter(activo=True).order_by("-creado_en", "-id")[:12]
    )
    for p in nuevos_productos:
        notificaciones.append(
            {
                "tipo": "producto",
                "titulo": "Nuevo producto en la tienda",
                "detalle": p.nombre,
                "fecha": p.creado_en.date(),
                "estado": "Disponible" if p.stock > 0 else "Agotado",
            }
        )

    notificaciones.sort(
        key=lambda n: (
            n.get("fecha") or date.min,
            1 if n.get("tipo") == "producto" else 2,
        ),
        reverse=True,
    )
    notificaciones = notificaciones[:120]
    return render(
        request,
        "frontend/cliente/notificaciones.html",
        {"notificaciones": notificaciones},
    )


@_cliente_login_required
def carrito_page(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    svc = get_carrito_lineas_service()
    items = svc.listar_items(uid)
    total = Decimal("0")
    for it in items:
        total += Decimal(it.get("subtotal_linea", "0"))
    return render(
        request,
        "frontend/cliente/carrito.html",
        {
            "carrito_items": items,
            "carrito_total": total,
            "usuario_id": uid,
        },
    )


@_cliente_login_required
@require_POST
def carrito_actualizar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    wants_json = _wants_json_response(request)
    try:
        detalle_id = int(request.POST.get("detalle_id", 0))
        cantidad = int(request.POST.get("cantidad", 1))
    except (TypeError, ValueError):
        if wants_json:
            return JsonResponse({"ok": False, "message": "Datos no válidos."}, status=400)
        messages.error(request, "Datos no válidos.")
        return redirect("web_carrito")
    try:
        get_carrito_lineas_service().actualizar_cantidad(uid, detalle_id, cantidad)
        if wants_json:
            return JsonResponse({"ok": True, "message": "Cantidad actualizada."})
        messages.success(request, "Cantidad actualizada.")
    except ValueError as exc:
        if wants_json:
            return JsonResponse({"ok": False, "message": str(exc)}, status=400)
        messages.error(request, str(exc))
    return redirect("web_carrito")


@_cliente_login_required
@require_POST
def carrito_eliminar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    wants_json = _wants_json_response(request)
    try:
        detalle_id = int(request.POST.get("detalle_id", 0))
    except (TypeError, ValueError):
        if wants_json:
            return JsonResponse({"ok": False, "message": "Ítem no válido."}, status=400)
        messages.error(request, "Ítem no válido.")
        return redirect("web_carrito")
    try:
        get_carrito_lineas_service().eliminar_detalle(uid, detalle_id)
        if wants_json:
            return JsonResponse({"ok": True, "message": "Producto eliminado del carrito."})
        messages.success(request, "Producto eliminado del carrito.")
    except ValueError as exc:
        if wants_json:
            return JsonResponse({"ok": False, "message": str(exc)}, status=400)
        messages.error(request, str(exc))
    return redirect("web_carrito")


@_cliente_login_required
@require_POST
def carrito_vaciar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    get_carrito_lineas_service().vaciar(uid)
    messages.success(request, "Carrito vaciado.")
    return redirect("web_carrito")


@_cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_informacion(request):
    """GET/POST /checkout/informacion — layout Spring + sesión checkout_informacion."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = _carrito_productos_total_spring(uid)
    if not productos:
        messages.warning(request, "Tu carrito está vacío. Agrega productos antes de pagar.")
        return redirect("web_carrito")
    usuario = get_object_or_404(Usuario, pk=uid)
    info = request.session.get(SESSION_CK_INFO) or {}
    doc_type = _doc_tipo_checkout(usuario, info)
    if request.method == "POST":
        request.session[SESSION_CK_INFO] = {
            "firstName": (request.POST.get("firstName") or "").strip(),
            "lastName": (request.POST.get("lastName") or "").strip(),
            "email": (request.POST.get("email") or "").strip(),
            "phone": (request.POST.get("phone") or "").strip(),
            "documentType": (request.POST.get("documentType") or "CC").strip(),
            "documentNumber": (request.POST.get("documentNumber") or "").strip(),
        }
        request.session.modified = True
        return redirect("web_cliente_checkout_direccion")
    return render(
        request,
        "frontend/checkout/checkout_informacion.html",
        {
            "step": "informacion",
            "usuario": usuario,
            "info": info,
            "doc_type": doc_type,
            "productos": productos,
            "total_carrito": total_carrito,
        },
    )


@_cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_direccion(request):
    """GET/POST /checkout/direccion — sesión checkout_direccion."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = _carrito_productos_total_spring(uid)
    if not productos:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect("web_carrito")
    if not request.session.get(SESSION_CK_INFO):
        messages.warning(request, "Completa primero tus datos personales.")
        return redirect("web_cliente_checkout_info")
    direccion = request.session.get(SESSION_CK_DIR) or {}
    if request.method == "POST":
        request.session[SESSION_CK_DIR] = {
            "departamento": (request.POST.get("departamento") or "").strip(),
            "ciudad": (request.POST.get("ciudad") or "").strip(),
            "direccion": (request.POST.get("direccion") or "").strip(),
            "localidad": (request.POST.get("localidad") or "").strip(),
            "barrio": (request.POST.get("barrio") or "").strip(),
        }
        request.session.modified = True
        return redirect("web_cliente_checkout_envio")
    return render(
        request,
        "frontend/checkout/checkout_direccion.html",
        {
            "step": "direccion",
            "usuario": get_object_or_404(Usuario, pk=uid),
            "direccion": direccion,
            "productos": productos,
            "total_carrito": total_carrito,
        },
    )


@_cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_envio(request):
    """GET/POST /checkout/envio — transportadora + fecha (como Spring)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = _carrito_productos_total_spring(uid)
    if not productos:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect("web_carrito")
    if not request.session.get(SESSION_CK_DIR):
        messages.warning(request, "Completa primero la dirección de envío.")
        return redirect("web_cliente_checkout_direccion")
    direccion = request.session.get(SESSION_CK_DIR) or {}
    envio = request.session.get(SESSION_CK_ENV) or {}
    if request.method == "POST":
        transportadora = (request.POST.get("transportadora") or "").strip()
        fecha_envio = (request.POST.get("fechaEnvio") or "").strip()
        if not transportadora or not fecha_envio:
            messages.error(request, "Selecciona transportadora y fecha de envío.")
            return redirect("web_cliente_checkout_envio")
        request.session[SESSION_CK_ENV] = {
            "transportadora": transportadora,
            "fechaEnvio": fecha_envio,
        }
        request.session.modified = True
        return redirect("web_cliente_checkout_pago")
    return render(
        request,
        "frontend/checkout/checkout_envio.html",
        {
            "step": "envio",
            "usuario": get_object_or_404(Usuario, pk=uid),
            "direccion": direccion,
            "envio": envio,
            "productos": productos,
            "total_carrito": total_carrito,
        },
    )


@_cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_pago(request):
    """GET/POST /checkout/pago — PayPal sandbox en sesión checkout_pago."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = _carrito_productos_total_spring(uid)
    if not productos:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect("web_carrito")
    if not request.session.get(SESSION_CK_ENV):
        messages.error(request, "Completa primero el método de envío.")
        return redirect("web_cliente_checkout_envio")
    if request.method == "POST":
        metodo = (request.POST.get("metodoPago") or request.POST.get("metodo_pago") or "paypal_sandbox").strip()
        request.session[SESSION_CK_PAGO] = {"metodoPago": metodo}
        request.session.modified = True
        return redirect("web_cliente_checkout_revision")
    return render(
        request,
        "frontend/checkout/checkout_pago.html",
        {
            "step": "pago",
            "usuario": get_object_or_404(Usuario, pk=uid),
            "productos": productos,
            "total_carrito": total_carrito,
        },
    )


@_cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_revision(request):
    """GET /checkout/revision — resumen (Spring)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = _carrito_productos_total_spring(uid)
    if not productos:
        messages.warning(request, "Tu carrito está vacío.")
        return redirect("web_carrito")
    if not request.session.get(SESSION_CK_PAGO):
        messages.error(request, "Selecciona una forma de pago.")
        return redirect("web_cliente_checkout_pago")
    usuario = get_object_or_404(Usuario, pk=uid)
    info = request.session.get(SESSION_CK_INFO) or {}
    direccion = request.session.get(SESSION_CK_DIR) or {}
    envio = request.session.get(SESSION_CK_ENV) or {}
    pago = request.session.get(SESSION_CK_PAGO) or {}
    metodo_raw = pago.get("metodoPago") or ""
    metodo_label = "PayPal Sandbox" if metodo_raw == "paypal_sandbox" else (metodo_raw or "—")
    return render(
        request,
        "frontend/checkout/checkout_revision.html",
        {
            "step": "revision",
            "usuario": usuario,
            "info": info,
            "direccion": direccion,
            "envio": envio,
            "pago": pago,
            "productos": productos,
            "total_carrito": total_carrito,
            "metodo_label": metodo_label,
        },
    )


@_cliente_login_required
@require_POST
def checkout_finalizar(request):
    """POST /checkout/finalizar — CheckoutService + limpieza de sesión (Spring)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    pago = request.session.get(SESSION_CK_PAGO) or {}
    metodo = (pago.get("metodoPago") or "").strip()
    if metodo == "paypal_sandbox":
        return redirect("web_cliente_checkout_paypal_iniciar")
    return _ejecutar_checkout_desde_sesion(request, uid)


@_cliente_login_required
def checkout_paypal_iniciar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    pago = request.session.get(SESSION_CK_PAGO) or {}
    if (pago.get("metodoPago") or "").strip() != "paypal_sandbox":
        messages.error(request, "El metodo de pago seleccionado no es PayPal Sandbox.")
        return redirect("web_cliente_checkout_revision")
    if not _paypal_is_configured():
        messages.error(request, "PayPal no esta configurado. Define TECHNOVA_PAYPAL_CLIENT_ID y TECHNOVA_PAYPAL_CLIENT_SECRET.")
        return redirect("web_cliente_checkout_revision")
    _, total_carrito = _carrito_productos_total_spring(uid)
    if total_carrito <= 0:
        messages.error(request, "No hay total valido para procesar en PayPal.")
        return redirect("web_cliente_checkout_revision")
    user = get_object_or_404(Usuario, pk=uid)
    reference = f"WEB-{uid}-{uuid.uuid4().hex[:10].upper()}"
    return_url = request.build_absolute_uri(reverse("web_cliente_checkout_paypal_retorno"))
    cancel_url = request.build_absolute_uri(reverse("web_cliente_checkout_paypal_retorno")) + "?cancel=true"
    try:
        order_id, approval_url = _paypal_create_order(
            amount=total_carrito,
            reference_code=reference,
            customer_email=user.correo_electronico,
            return_url=return_url,
            cancel_url=cancel_url,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("web_cliente_checkout_revision")
    request.session[SESSION_CK_PAYPAL] = {"order_id": order_id}
    request.session.modified = True
    return redirect(approval_url)


@_cliente_login_required
def checkout_paypal_retorno(request):
    if (request.GET.get("cancel") or "").lower() in {"true", "1", "yes"}:
        messages.warning(request, "Pago cancelado en PayPal Sandbox.")
        return redirect("web_cliente_checkout_revision")
    paypal_data = request.session.get(SESSION_CK_PAYPAL) or {}
    expected_order_id = (paypal_data.get("order_id") or "").strip()
    token = (request.GET.get("token") or "").strip()
    order_id = token or expected_order_id
    if not order_id:
        messages.error(request, "No se recibio orderId desde PayPal.")
        return redirect("web_cliente_checkout_revision")
    if expected_order_id and expected_order_id != order_id:
        messages.error(request, "El orderId devuelto por PayPal no coincide con la sesion.")
        return redirect("web_cliente_checkout_revision")
    ok, status = _paypal_capture_order(order_id)
    if not ok:
        messages.error(request, f"No se pudo capturar el pago en PayPal ({status}).")
        return redirect("web_cliente_checkout_revision")
    uid = request.session.get(SESSION_USUARIO_ID)
    numero_factura_pp = _numero_factura_desde_paypal_order(order_id, int(uid or 0))
    return _ejecutar_checkout_desde_sesion(request, uid, numero_factura=numero_factura_pp)


@_cliente_login_required
def checkout_confirmacion(request):
    """Pantalla de éxito alineada al modal Spring (sin carrito)."""
    data = request.session.pop(SESSION_CK_RESULT, None)
    if not data:
        return redirect("web_cliente_pedidos")
    return render(
        request,
        "frontend/checkout/checkout_confirmacion.html",
        {
            "venta_id": data.get("venta_id"),
            "total": data.get("total"),
            "idempotente": data.get("idempotente"),
        },
    )


@_cliente_login_required
def pedidos_cliente(request):
    """Pedidos = ventas del usuario (equivalente a cliente/pedidos en Java)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    raw = get_venta_query_service().listar_ventas_por_usuario(uid)
    id_productos = set()
    for v in raw:
        for d in v.get("detalles", []):
            id_productos.add(d["producto_id"])
    nombres = {
        pid: Producto.objects.filter(pk=pid).values_list("nombre", flat=True).first() or "Producto"
        for pid in id_productos
    }
    pedidos = []
    for v in raw:
        detalles_enriquecidos = []
        for d in v.get("detalles", []):
            pu = Decimal(str(d.get("precio_unitario", "0")))
            cant = int(d.get("cantidad", 0))
            precio_linea = pu * cant
            detalles_enriquecidos.append(
                {
                    "producto_id": d["producto_id"],
                    "cantidad": cant,
                    "precio_unitario": d.get("precio_unitario", "0"),
                    "nombre_producto": nombres.get(d["producto_id"], "Producto"),
                    "precio_linea": precio_linea,
                }
            )
        fv = v.get("fecha_venta", "")
        try:
            fecha_fmt = datetime.fromisoformat(str(fv)).strftime("%d/%m/%Y") if fv else ""
        except ValueError:
            fecha_fmt = str(fv)
        pedidos.append(
            {
                "venta_id": v["id"],
                "fecha_venta": fecha_fmt,
                "total": v.get("total", "0"),
                "estado": v.get("estado", ""),
                "items": detalles_enriquecidos,
            }
        )
    return render(request, "frontend/cliente/pedidos.html", {"pedidos": pedidos})


@_cliente_login_required
def mis_compras(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    ventas = list(
        Venta.objects.filter(usuario_id=uid)
        .select_related("usuario")
        .prefetch_related("detalles__producto")
        .order_by("-fecha_venta", "-id")[:120]
    )
    rows = []
    for venta in ventas:
        pago = (
            Pago.objects.filter(medios_pago__detalle_venta__venta_id=venta.id)
            .distinct()
            .order_by("-fecha_pago", "-id")
            .first()
        )
        envio = (
            Envio.objects.filter(venta_id=venta.id, activo=True)
            .select_related("transportadora")
            .order_by("-fecha_envio", "-id")
            .first()
        )
        rows.append(
            {
                "venta": venta,
                "pago": pago,
                "envio": envio,
                "items_count": venta.detalles.count(),
            }
        )
    return render(
        request,
        "frontend/cliente/mis_compras.html",
        {"rows": rows},
    )


@_cliente_login_required
def cliente_factura_compra(request, venta_id: int):
    uid = request.session.get(SESSION_USUARIO_ID)
    venta = get_object_or_404(
        Venta.objects.select_related("usuario").prefetch_related("detalles__producto"),
        pk=venta_id,
        usuario_id=uid,
    )
    pago = (
        Pago.objects.filter(medios_pago__detalle_venta__venta_id=venta.id)
        .distinct()
        .order_by("-fecha_pago", "-id")
        .first()
    )
    if pago is None:
        messages.error(request, "Aún no hay factura de pago disponible para esta compra.")
        return redirect("web_cliente_mis_compras")
    lineas = [
        {
            "nombre": d.producto.nombre,
            "cantidad": d.cantidad,
            "precio_unitario": d.precio_unitario,
            "subtotal": d.precio_unitario * d.cantidad,
        }
        for d in venta.detalles.select_related("producto").all()
    ]
    return render(
        request,
        "frontend/cliente/factura_compra.html",
        {
            "venta": venta,
            "pago": pago,
            "cliente": venta.usuario,
            "lineas": lineas,
        },
    )


@_cliente_login_required
def atencion_cliente(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)

    # Tickets (solicitudes)
    tickets_raw = get_atencion_query_service().listar_solicitudes(uid)
    tickets = [
        {
            "id": t.get("id"),
            "tema": t.get("tema") or "",
            "descripcion": t.get("descripcion") or "",
            "fechaConsulta": t.get("fechaConsulta") or t.get("fecha_consulta"),
            "respuesta": t.get("respuesta") or "",
            "estado": (t.get("estado") or "").strip().lower(),
        }
        for t in (tickets_raw or [])
    ]

    # Conversaciones (tomar el último mensaje por conversación)
    md_items = get_mensajeria_query_service().listar_mensajes_directos(uid) or []
    por_conv: dict[str, dict] = {}
    for m in md_items:
        cid = m.get("conversationId") or m.get("conversacion_id")
        if not cid:
            continue
        prev = por_conv.get(cid)
        if prev is None or (m.get("createdAt") or "") > (prev.get("createdAt") or ""):
            por_conv[cid] = m
    conversaciones = sorted(por_conv.values(), key=lambda x: x.get("createdAt") or "", reverse=True)

    # Normalizar keys a lo que usa el HTML/JS de referencia (Java)
    conversaciones_norm = []
    for c in conversaciones:
        conversaciones_norm.append(
            {
                "conversationId": c.get("conversationId"),
                "id": c.get("id"),
                "asunto": c.get("subject") or c.get("asunto") or "",
                "mensaje": c.get("message") or c.get("mensaje") or "",
                "prioridad": c.get("priority") or c.get("prioridad") or "normal",
                "estado": c.get("state") or c.get("estado") or "enviado",
                "isRead": bool(c.get("isRead") or c.get("leido")),
                "senderType": c.get("senderType") or c.get("tipo_remitente") or "cliente",
                "createdAt": c.get("createdAt"),
            }
        )

    return render(
        request,
        "frontend/cliente/atencion-cliente.html",
        {
            "usuario": usuario,
            "tickets": tickets,
            "conversaciones": conversaciones_norm,
            "usuario_id": uid,
        },
    )


@_cliente_login_required
def cliente_reclamos(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)
    reclamos_raw = get_atencion_query_service().listar_reclamos(uid) or []
    reclamos = sorted(reclamos_raw, key=lambda x: x.get("fechaReclamo") or "", reverse=True)
    return render(
        request,
        "frontend/cliente/reclamos.html",
        {
            "usuario": usuario,
            "usuario_id": uid,
            "reclamos": reclamos,
        },
    )


def producto_detalle(request, producto_id: int):
    """Detalle público del producto (catálogo); datos vía API en cliente."""
    return render(
        request,
        "frontend/cliente/producto_detalle.html",
        {
            "producto_id": producto_id,
            "usuario_id": request.session.get(SESSION_USUARIO_ID),
        },
    )
