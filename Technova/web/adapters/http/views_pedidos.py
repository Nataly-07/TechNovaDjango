from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from common.container import get_venta_query_service
from envio.models import Envio
from pago.models import Pago
from producto.models import Producto
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from venta.models import Venta

from web.adapters.http.decorators import cliente_login_required


@cliente_login_required
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


@cliente_login_required
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


@cliente_login_required
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


@cliente_login_required
def atencion_cliente(request):
    return render(request, "frontend/cliente/atencion.html")


@cliente_login_required
def producto_detalle(request, producto_id: int):
    return render(request, "frontend/cliente/producto_detalle.html", {"producto_id": producto_id})
