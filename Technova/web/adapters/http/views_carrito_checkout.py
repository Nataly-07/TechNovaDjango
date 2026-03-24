import uuid
from decimal import Decimal

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST, require_http_methods

from common.container import get_carrito_lineas_service
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.infrastructure.models.usuario_model import Usuario

from web.application.checkout_web_service import (
    carrito_productos_total_spring,
    doc_tipo_checkout,
    ejecutar_checkout_desde_sesion,
    paypal_capture_order,
    paypal_create_order,
    paypal_is_configured,
)
from web.application.request_helpers import wants_json_response
from web.domain.constants import (
    SESSION_CK_DIR,
    SESSION_CK_ENV,
    SESSION_CK_INFO,
    SESSION_CK_PAGO,
    SESSION_CK_PAYPAL,
    SESSION_CK_RESULT,
)
from web.adapters.http.decorators import cliente_login_required


@cliente_login_required
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


@cliente_login_required
@require_POST
def carrito_actualizar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    wants_json = wants_json_response(request)
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


@cliente_login_required
@require_POST
def carrito_eliminar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    wants_json = wants_json_response(request)
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


@cliente_login_required
@require_POST
def carrito_vaciar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    get_carrito_lineas_service().vaciar(uid)
    messages.success(request, "Carrito vaciado.")
    return redirect("web_carrito")


@cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_informacion(request):
    """GET/POST /checkout/informacion — layout Spring + sesión checkout_informacion."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = carrito_productos_total_spring(uid)
    if not productos:
        messages.warning(request, "Tu carrito está vacío. Agrega productos antes de pagar.")
        return redirect("web_carrito")
    usuario = get_object_or_404(Usuario, pk=uid)
    info = request.session.get(SESSION_CK_INFO) or {}
    doc_type = doc_tipo_checkout(usuario, info)
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


@cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_direccion(request):
    """GET/POST /checkout/direccion — sesión checkout_direccion."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = carrito_productos_total_spring(uid)
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


@cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_envio(request):
    """GET/POST /checkout/envio — transportadora + fecha (como Spring)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = carrito_productos_total_spring(uid)
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


@cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_pago(request):
    """GET/POST /checkout/pago — PayPal sandbox en sesión checkout_pago."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = carrito_productos_total_spring(uid)
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


@cliente_login_required
@require_http_methods(["GET", "POST"])
def checkout_revision(request):
    """GET /checkout/revision — resumen (Spring)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    productos, total_carrito = carrito_productos_total_spring(uid)
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
    metodo_label = (
        "PayPal Sandbox"
        if metodo_raw == "paypal_sandbox"
        else (metodo_raw or "—")
    )
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


@cliente_login_required
@require_POST
def checkout_finalizar(request):
    """POST /checkout/finalizar — CheckoutService + limpieza de sesión (Spring)."""
    uid = request.session.get(SESSION_USUARIO_ID)
    pago = request.session.get(SESSION_CK_PAGO) or {}
    if (pago.get("metodoPago") or "").strip() == "paypal_sandbox":
        return redirect("web_cliente_checkout_paypal_iniciar")
    return ejecutar_checkout_desde_sesion(request, uid)


@cliente_login_required
def checkout_paypal_iniciar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    pago = request.session.get(SESSION_CK_PAGO) or {}
    if (pago.get("metodoPago") or "").strip() != "paypal_sandbox":
        messages.error(request, "El metodo de pago seleccionado no es PayPal Sandbox.")
        return redirect("web_cliente_checkout_revision")
    if not paypal_is_configured():
        messages.error(request, "PayPal no esta configurado. Define TECHNOVA_PAYPAL_CLIENT_ID y TECHNOVA_PAYPAL_CLIENT_SECRET.")
        return redirect("web_cliente_checkout_revision")
    _, total_carrito = carrito_productos_total_spring(uid)
    if total_carrito <= 0:
        messages.error(request, "No hay total valido para procesar en PayPal.")
        return redirect("web_cliente_checkout_revision")
    user = get_object_or_404(Usuario, pk=uid)
    reference = f"WEB-{uid}-{uuid.uuid4().hex[:10].upper()}"
    return_url = request.build_absolute_uri(reverse("web_cliente_checkout_paypal_retorno"))
    cancel_url = request.build_absolute_uri(reverse("web_cliente_checkout_paypal_retorno")) + "?cancel=true"
    try:
        order_id, approval_url = paypal_create_order(
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


@cliente_login_required
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
    ok, status = paypal_capture_order(order_id)
    if not ok:
        messages.error(request, f"No se pudo capturar el pago en PayPal ({status}).")
        return redirect("web_cliente_checkout_revision")
    uid = request.session.get(SESSION_USUARIO_ID)
    return ejecutar_checkout_desde_sesion(request, uid)


@cliente_login_required
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
