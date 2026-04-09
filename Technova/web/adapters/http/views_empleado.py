import json
import uuid
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.urls import reverse

from pago.models import MedioPago, Pago
from producto.models import Producto

from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.application.use_cases.autenticacion_usecases import credenciales_coinciden
from usuario.infrastructure.models.usuario_model import Usuario
from venta.models import DetalleVenta, Venta

from correos.compra_notificacion_service import enviar_correo_compra_confirmada_cliente
from web.application.checkout_web_service import (
    paypal_capture_order,
    paypal_create_order,
    paypal_is_configured,
)
from web.application.pos_cliente_service import resolver_cliente_para_pos

from web.domain.constants import EMPLEADO_SECCIONES
from web.adapters.http.decorators import empleado_login_required


def _pos_numero_factura(cliente_id: int) -> str:
    return f"POS-{timezone.localdate().year}-{cliente_id}-{uuid.uuid4().hex[:10].upper()}"


def _pos_parse_items(items_json: str) -> list[dict]:
    raw = json.loads(items_json or "[]")
    if not isinstance(raw, list) or not raw:
        raise ValueError("Debes agregar al menos un producto.")
    out: list[dict] = []
    for it in raw:
        pid = int(it.get("producto_id") or 0)
        cant = int(it.get("cantidad") or 0)
        if pid <= 0 or cant <= 0:
            raise ValueError("Items inválidos.")
        out.append({"producto_id": pid, "cantidad": cant})
    return out


@transaction.atomic
def _pos_registrar_venta(
    *,
    cliente_id: int,
    items: list[dict],
    empleado_id: int,
    metodo_pago: str,
    numero_factura: str,
    datos_facturacion_mostrador: dict | None = None,
) -> tuple[int, int]:
    detalles_creados: list[DetalleVenta] = []
    total = Decimal("0")

    venta = Venta.objects.create(
        usuario_id=cliente_id,
        tipo_venta=Venta.TipoVenta.FISICA,
        empleado_id=empleado_id,
        fecha_venta=timezone.localdate(),
        estado=Venta.Estado.FACTURADA,
        total=Decimal("0"),
        datos_facturacion_mostrador=datos_facturacion_mostrador,
    )

    for it in items:
        p = Producto.objects.select_for_update().filter(pk=it["producto_id"], activo=True).first()
        if not p:
            raise ValueError("Producto no disponible.")
        cant = int(it["cantidad"])
        if p.stock < cant:
            raise ValueError(f"Stock insuficiente para {p.nombre}.")

        pu = p.precio_publico if p.precio_publico is not None else p.costo_unitario
        subtotal = pu * cant
        total += subtotal

        detalle = DetalleVenta.objects.create(
            venta=venta,
            producto=p,
            cantidad=cant,
            precio_unitario=pu,
        )
        detalles_creados.append(detalle)

        p.stock -= cant
        p.save(update_fields=["stock", "actualizado_en"])

    venta.total = total
    venta.save(update_fields=["total", "actualizado_en"])

    pago = Pago.objects.create(
        fecha_pago=timezone.localdate(),
        numero_factura=numero_factura,
        fecha_factura=timezone.localdate(),
        monto=total,
        estado_pago=Pago.EstadoPago.APROBADO,
    )

    for d in detalles_creados:
        MedioPago.objects.create(
            pago=pago,
            detalle_venta=d,
            usuario_id=cliente_id,
            metodo_pago=metodo_pago,
            fecha_compra=timezone.now(),
            tiempo_entrega=None,
            activo=True,
        )

    def _correo_cliente_pos() -> None:
        enviar_correo_compra_confirmada_cliente(
            venta_id=venta.id,
            pago_id=pago.id,
            canal="punto_fisico",
        )

    transaction.on_commit(_correo_cliente_pos)

    return venta.id, pago.id


@empleado_login_required
def empleado_dashboard(request, seccion: str = "inicio"):
    """Shell del panel empleado (misma base visual que admin); módulos sin implementar."""
    if seccion not in EMPLEADO_SECCIONES:
        return redirect("web_empleado_inicio")
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = Usuario.objects.get(pk=uid)

    ctx = {
        "usuario": usuario,
        "seccion": seccion,
        "titulo_seccion": EMPLEADO_SECCIONES[seccion],
    }

    if seccion == "punto-venta":
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
                items = _pos_parse_items(request.POST.get("items_json") or "[]")
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

            numero_factura = _pos_numero_factura(cliente_id)
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
                venta_id, _pago_id = _pos_registrar_venta(
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


@empleado_login_required
def empleado_pos_paypal_retorno(request):
    data = request.session.get("pos_paypal") or {}
    order_id = (request.GET.get("token") or data.get("order_id") or "").strip()
    if not order_id or not data:
        messages.error(request, "No se encontró una transacción PayPal pendiente.")
        return redirect("web_empleado_seccion", seccion="punto-venta")

    ok, status = paypal_capture_order(order_id)
    if not ok:
        messages.error(request, f"No se pudo confirmar el pago PayPal ({status}).")
        request.session.pop("pos_paypal", None)
        request.session.modified = True
        return redirect("web_empleado_seccion", seccion="punto-venta")

    uid = request.session.get(SESSION_USUARIO_ID)
    empleado = Usuario.objects.get(pk=uid)

    try:
        venta_id, _pago_id = _pos_registrar_venta(
            cliente_id=int(data["cliente_id"]),
            items=list(data["items"]),
            empleado_id=empleado.id,
            metodo_pago=MedioPago.Metodo.PAYPAL.value,
            numero_factura=str(data["numero_factura"]),
            datos_facturacion_mostrador=data.get("datos_facturacion_mostrador"),
        )
    except (KeyError, ValueError) as exc:
        messages.error(request, str(exc))
        return redirect("web_empleado_seccion", seccion="punto-venta")
    finally:
        request.session.pop("pos_paypal", None)
        request.session.modified = True

    messages.success(
        request,
        f"Pago PayPal confirmado. Venta registrada. Factura: {data.get('numero_factura')}",
    )
    return redirect("web_empleado_pos_factura", venta_id=venta_id)


@empleado_login_required
def empleado_pos_factura(request, venta_id: int):
    uid = request.session.get(SESSION_USUARIO_ID)
    empleado = Usuario.objects.get(pk=uid)

    venta = get_object_or_404(
        Venta.objects.select_related("usuario").prefetch_related("detalles__producto"),
        pk=venta_id,
        empleado_id=empleado.id,
        tipo_venta=Venta.TipoVenta.FISICA,
    )
    pago = (
        Pago.objects.filter(medios_pago__detalle_venta__venta_id=venta.id)
        .distinct()
        .order_by("-fecha_pago", "-id")
        .first()
    )
    if pago is None:
        messages.error(request, "Aún no hay factura de pago disponible para esta venta.")
        return redirect("web_empleado_seccion", seccion="punto-venta")

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
        "frontend/empleado/factura_pos.html",
        {
            "venta": venta,
            "pago": pago,
            "cliente": venta.usuario,
            "lineas": lineas,
            "empleado": empleado,
        },
    )


@empleado_login_required
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
