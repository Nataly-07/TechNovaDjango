"""
Recepción / validación de mercancía de órdenes de compra (admin y empleado).
"""

from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from orden.application.recepcion_orden_service import RecepcionOrdenError, validar_recepcion_mercancia
from orden.infrastructure.models import OrdenCompra
from usuario.infrastructure.models.usuario_model import Usuario
from web.adapters.http.decorators import admin_o_empleado_login_required, empleado_login_required


def _uid_sesion(request):
    from usuario.adapters.web.session_views import SESSION_USUARIO_ID

    return request.session.get(SESSION_USUARIO_ID)


@empleado_login_required
@require_http_methods(["GET"])
def empleado_ordenes_compra_lista(request):
    """Listado de órdenes de compra para el empleado (recepción)."""
    ordenes = (
        OrdenCompra.objects.select_related("proveedor")
        .prefetch_related("detalles")
        .order_by("-fecha", "-id")[:200]
    )
    uid = _uid_sesion(request)
    usuario = Usuario.objects.get(pk=uid)
    return render(
        request,
        "frontend/empleado/ordenes_compra_lista.html",
        {
            "usuario": usuario,
            "seccion": "ordenes-compra",
            "ordenes": ordenes,
        },
    )


@admin_o_empleado_login_required
@require_http_methods(["GET", "POST"])
def validar_recepcion_orden_compra(request, orden_id: int):
    usuario: Usuario = request.usuario_sesion  # type: ignore[attr-defined]
    orden = get_object_or_404(
        OrdenCompra.objects.select_related("proveedor", "recepcion_validada_por").prefetch_related("detalles__producto"),
        pk=orden_id,
    )

    if request.method == "POST":
        if orden.estado != OrdenCompra.Estado.PENDIENTE:
            messages.error(request, "Esta orden ya no admite validación de recepción.")
            return redirect(request.path)

        cantidades: dict[int, int] = {}
        for det in orden.detalles.all():
            key = f"cantidad_recibida_{det.id}"
            raw = request.POST.get(key, "")
            try:
                qty = int(raw) if str(raw).strip() != "" else int(det.cantidad)
            except (TypeError, ValueError):
                messages.error(request, f"Cantidad recibida no válida para «{det.producto.nombre}».")
                return redirect(request.path)
            cantidades[det.id] = qty

        obs = (request.POST.get("observaciones_recepcion") or "").strip()
        try:
            with transaction.atomic():
                validar_recepcion_mercancia(
                    orden.id,
                    usuario_id=usuario.id,
                    cantidades_por_detalle_id=cantidades,
                    observaciones=obs,
                )
        except RecepcionOrdenError as e:
            messages.error(request, str(e))
            return redirect(request.path)

        messages.success(request, "Recepción validada. El inventario se actualizó y la orden quedó completada.")
        if usuario.rol == Usuario.Rol.ADMIN:
            return redirect("web_admin_ordenes_compra")
        return redirect("web_empleado_ordenes_compra")

    es_empleado = usuario.rol == Usuario.Rol.EMPLEADO
    tpl = (
        "frontend/empleado/validar_recepcion_orden.html"
        if es_empleado
        else "frontend/admin/ordenes/validar_recepcion_orden.html"
    )
    return render(
        request,
        tpl,
        {
            "usuario": usuario,
            "seccion": "ordenes-compra",
            "orden": orden,
            "detalles": list(orden.detalles.all()),
            "es_empleado": es_empleado,
        },
    )
