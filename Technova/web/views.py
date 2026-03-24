import json
import re
import uuid
import base64
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from django.contrib import messages
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Count, Prefetch, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from django.utils.safestring import mark_safe
from django.urls import reverse

from carrito.models import Carrito, Favorito
from common.container import (
    get_carrito_lineas_service,
    get_carrito_query_service,
    get_checkout_service,
    get_producto_service,
    get_proveedor_service,
    get_venta_query_service,
)
from compra.models import Compra, DetalleCompra
from envio.models import Envio, Transportadora
from mensajeria.models import MensajeDirecto
from pago.models import MedioPago, MetodoPagoUsuario, Pago
from producto.domain.entities import ProductoEntidad
from producto.models import Producto, ProductoCatalogoExtra
from proveedor.domain.entities import ProveedorEntidad
from proveedor.models import Proveedor
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.application.registro_usuario_service import registrar_usuario_desde_payload
from usuario.application.use_cases.autenticacion_usecases import credenciales_coinciden
from usuario.infrastructure.models.usuario_model import Usuario
from venta.models import Venta

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
    except IntegrityError:
        messages.error(request, "No se pudo registrar el pedido. Intentalo de nuevo.")
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
        venta = Venta.objects.select_related("usuario").filter(pk=vid).first()
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
    "mensajes": "Mensajes",
    "productos": "Visualización de artículos",
    "pedidos": "Pedidos",
    "venta-punto-fisico": "Venta punto físico",
    "atencion-cliente": "Atención al cliente",
    "notificaciones": "Notificaciones",
}


@_empleado_login_required
def empleado_dashboard(request, seccion: str = "inicio"):
    """Shell del panel empleado (misma base visual que admin); módulos sin implementar."""
    if seccion not in EMPLEADO_SECCIONES:
        return redirect("web_empleado_inicio")
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)
    return render(
        request,
        "frontend/empleado/dashboard.html",
        {
            "usuario": usuario,
            "seccion": seccion,
            "titulo_seccion": EMPLEADO_SECCIONES[seccion],
        },
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
        usuario.telefono = telefono
        usuario.direccion = direccion
        usuario.save(update_fields=["telefono", "direccion", "actualizado_en"])
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
    carrito_preview = []
    for it in get_carrito_lineas_service().listar_items(uid)[:8]:
        carrito_preview.append(
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
    return JsonResponse({"ok": True, "message": "Producto agregado al carrito."})


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
def perfil_admin(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)
    mensajes_pendientes = MensajeDirecto.objects.exclude(
        estado=MensajeDirecto.Estado.RESPONDIDO
    ).count()
    ctx = {
        "usuario": usuario,
        "users_count": Usuario.objects.count(),
        "productos_count": Producto.objects.filter(activo=True).count(),
        "proveedores_count": Proveedor.objects.filter(activo=True).count(),
        "reportes_disponibles": 3,
        "mensajes_pendientes": mensajes_pendientes,
        "pedidos_procesados": Venta.objects.count(),
        "transacciones_procesadas": Pago.objects.count(),
    }
    return render(request, "frontend/admin/perfil.html", ctx)


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

    qs = Producto.objects.select_related("proveedor").order_by("id")
    if categoria:
        qs = qs.filter(categoria__iexact=categoria)
    if busqueda:
        qs = qs.filter(Q(nombre__icontains=busqueda) | Q(codigo__icontains=busqueda))

    productos = list(qs)
    productos_json = json.dumps(
        [_producto_modal_dict(p) for p in productos],
        ensure_ascii=False,
    )

    total_productos = Producto.objects.count()
    productos_bajo_stock = Producto.objects.filter(activo=True, stock__gt=0, stock__lt=10).count()
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
        "productos": productos,
        "productos_json": mark_safe(productos_json),
        "categoria": categoria,
        "busqueda": busqueda,
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
    p.activo = activar
    p.save(update_fields=["activo", "actualizado_en"])
    messages.success(
        request,
        "Producto activado correctamente." if activar else "Producto desactivado correctamente.",
    )
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
                queryset=MedioPago.objects.select_related("detalle_venta__venta__usuario"),
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
        usuario.telefono = telefono
        usuario.direccion = direccion
        usuario.save(update_fields=["telefono", "direccion", "actualizado_en"])
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
    return _ejecutar_checkout_desde_sesion(request, uid)


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
    return render(request, "frontend/cliente/atencion.html")


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
