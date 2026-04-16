"""
Solicitudes Órdenes de Compra Prov — empleado (crear/enviar) y admin (revisar/aprobar/rechazar).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from orden.application.solicitud_oc_prov_service import (
    aplicar_snapshots_desde_producto,
    aprobar_y_generar_orden,
    enviar_solicitud_al_admin,
    rechazar_solicitud,
)
from orden.infrastructure.models import SolicitudOrdenCompraProv
from producto.models import Producto
from proveedor.models import Proveedor
from usuario.infrastructure.models.usuario_model import Usuario
from web.adapters.http.decorators import admin_login_required, empleado_login_required
from usuario.adapters.web.session_views import SESSION_USUARIO_ID

STOCK_BAJO_MAX = 2  # stock < 3


def _parse_costo_unitario(raw) -> Decimal | None:
    if raw is None:
        return None
    s = str(raw).strip().replace(",", ".")
    if not s:
        return None
    try:
        return Decimal(s).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def _empleado_uid(request):
    return request.session.get(SESSION_USUARIO_ID)


@empleado_login_required
@require_http_methods(["GET", "POST"])
def empleado_solicitudes_oc_prov_lista(request):
    """Listado + creación de solicitudes en edición antes de envío."""
    uid = _empleado_uid(request)
    empleado = get_object_or_404(Usuario, pk=uid, rol=Usuario.Rol.EMPLEADO)

    productos_bajo_stock = list(
        Producto.objects.filter(activo=True, stock__lte=STOCK_BAJO_MAX)
        .select_related("proveedor")
        .order_by("stock", "nombre")[:200]
    )
    productos_todos = list(
        Producto.objects.filter(activo=True).select_related("proveedor").order_by("nombre")[:500]
    )

    if request.method == "POST":
        producto_id = int(request.POST.get("producto_id") or 0)
        cantidad = int(request.POST.get("cantidad") or 0)
        comentario = (request.POST.get("comentario_empleado") or "").strip()
        if producto_id < 1 or cantidad < 1:
            messages.error(request, "Selecciona un producto y una cantidad válida.")
            return redirect("web_empleado_solicitudes_oc_prov")
        p = get_object_or_404(Producto, pk=producto_id, activo=True)
        sol = SolicitudOrdenCompraProv(
            empleado=empleado,
            producto=p,
            proveedor_id=p.proveedor_id,
            cantidad=cantidad,
            comentario_empleado=comentario,
            estado=SolicitudOrdenCompraProv.Estado.BORRADOR,
        )
        aplicar_snapshots_desde_producto(sol)
        costo_post = _parse_costo_unitario(request.POST.get("costo_unitario"))
        if costo_post is not None:
            if costo_post < 0:
                messages.error(request, "El costo unitario no puede ser negativo.")
                return redirect("web_empleado_solicitudes_oc_prov")
            sol.costo_unitario_snapshot = costo_post
        sol.save()
        messages.success(
            request,
            f"Solicitud #{sol.id} generada. Puedes revisarla y enviarla al administrador cuando esté lista.",
        )
        return redirect("web_empleado_solicitud_oc_prov_editar", solicitud_id=sol.id)

    solicitudes = (
        SolicitudOrdenCompraProv.objects.filter(empleado=empleado)
        .select_related("producto", "proveedor", "orden_compra")
        .order_by("-creado_en")[:100]
    )

    return render(
        request,
        "frontend/empleado/solicitudes_oc_prov.html",
        {
            "empleado": empleado,
            "usuario": empleado,
            "seccion": "solicitudes-oc-prov",
            "productos_bajo_stock": productos_bajo_stock,
            "productos_todos": productos_todos,
            "solicitudes": solicitudes,
            "stock_bajo_umbral": STOCK_BAJO_MAX,
        },
    )


@empleado_login_required
@require_http_methods(["GET", "POST"])
def empleado_solicitud_oc_prov_editar(request, solicitud_id: int):
    uid = _empleado_uid(request)
    sol = get_object_or_404(
        SolicitudOrdenCompraProv.objects.select_related("producto", "proveedor"),
        pk=solicitud_id,
        empleado_id=uid,
    )
    if sol.estado != SolicitudOrdenCompraProv.Estado.BORRADOR:
        messages.warning(request, "Esta solicitud ya no se puede editar.")
        return redirect("web_empleado_solicitudes_oc_prov")

    if request.method == "POST":
        cantidad = int(request.POST.get("cantidad") or 0)
        comentario = (request.POST.get("comentario_empleado") or "").strip()
        producto_id = int(request.POST.get("producto_id") or sol.producto_id)
        if cantidad < 1:
            messages.error(request, "La cantidad debe ser al menos 1.")
            return redirect("web_empleado_solicitud_oc_prov_editar", solicitud_id=sol.id)
        costo_post = _parse_costo_unitario(request.POST.get("costo_unitario"))
        if costo_post is None:
            messages.error(request, "Indica un costo unitario válido.")
            return redirect("web_empleado_solicitud_oc_prov_editar", solicitud_id=sol.id)
        if costo_post < 0:
            messages.error(request, "El costo unitario no puede ser negativo.")
            return redirect("web_empleado_solicitud_oc_prov_editar", solicitud_id=sol.id)
        p = get_object_or_404(Producto, pk=producto_id, activo=True)
        sol.producto = p
        sol.proveedor_id = p.proveedor_id
        sol.cantidad = cantidad
        sol.comentario_empleado = comentario
        aplicar_snapshots_desde_producto(sol, sobrescribir_costo_desde_catalogo=False)
        sol.costo_unitario_snapshot = costo_post
        sol.save()
        messages.success(request, "Los cambios en la solicitud se guardaron correctamente.")
        return redirect("web_empleado_solicitud_oc_prov_editar", solicitud_id=sol.id)

    productos = Producto.objects.filter(activo=True).select_related("proveedor").order_by("nombre")[:600]
    return render(
        request,
        "frontend/empleado/solicitud_oc_prov_editar.html",
        {
            "solicitud": sol,
            "productos": productos,
            "usuario": sol.empleado,
            "seccion": "solicitudes-oc-prov",
        },
    )


@empleado_login_required
@require_POST
def empleado_solicitud_oc_prov_enviar(request, solicitud_id: int):
    uid = _empleado_uid(request)
    sol = get_object_or_404(SolicitudOrdenCompraProv, pk=solicitud_id, empleado_id=uid)
    try:
        enviar_solicitud_al_admin(sol)
        messages.success(
            request,
            "Solicitud enviada exitosamente para revisión del Administrador.",
        )
    except ValueError as e:
        messages.error(request, str(e))
    return redirect("web_empleado_solicitudes_oc_prov")


@empleado_login_required
@require_GET
def empleado_api_producto_oc_prov(request, producto_id: int):
    p = get_object_or_404(Producto.objects.select_related("proveedor"), pk=producto_id, activo=True)
    costo = p.costo_unitario or Decimal("0")
    pv = p.precio_venta
    margen_pct = ""
    if costo > 0 and pv is not None:
        margen_pct = str(((pv / costo - Decimal("1")) * 100).quantize(Decimal("0.01")))
    return JsonResponse(
        {
            "id": p.id,
            "codigo": p.codigo,
            "nombre": p.nombre,
            "stock": p.stock,
            "marca": p.marca or "",
            "color": p.color or "",
            "costo_unitario": str(costo),
            "precio_venta": str(pv) if pv is not None else "",
            "margen_sobre_costo_pct": margen_pct,
            "proveedor_id": p.proveedor_id,
            "proveedor_nombre": p.proveedor.nombre if p.proveedor else "",
        }
    )


@admin_login_required
def admin_solicitudes_oc_prov_lista(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = get_object_or_404(Usuario, pk=uid, rol=Usuario.Rol.ADMIN)
    estado = (request.GET.get("estado") or "").strip()
    qs = SolicitudOrdenCompraProv.objects.select_related(
        "empleado", "producto", "proveedor", "orden_compra"
    ).order_by("-creado_en")
    if estado and estado in dict(SolicitudOrdenCompraProv.Estado.choices):
        qs = qs.filter(estado=estado)
    pendientes = SolicitudOrdenCompraProv.objects.filter(
        estado=SolicitudOrdenCompraProv.Estado.PENDIENTE
    ).count()
    total_filtrado = qs.count()
    return render(
        request,
        "frontend/admin/solicitudes_oc_prov_lista.html",
        {
            "usuario": usuario,
            "solicitudes": qs[:500],
            "pendientes_count": pendientes,
            "total_filtrado": total_filtrado,
            "estados": SolicitudOrdenCompraProv.Estado.choices,
            "estado_filtro": estado,
        },
    )


@admin_login_required
@require_http_methods(["GET", "POST"])
def admin_solicitud_oc_prov_detalle(request, solicitud_id: int):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = get_object_or_404(Usuario, pk=uid, rol=Usuario.Rol.ADMIN)
    sol = get_object_or_404(
        SolicitudOrdenCompraProv.objects.select_related("empleado", "producto", "proveedor", "orden_compra"),
        pk=solicitud_id,
    )
    proveedores = Proveedor.objects.filter(activo=True).order_by("nombre")

    if request.method == "POST":
        accion = (request.POST.get("accion") or "").strip()
        if sol.estado != SolicitudOrdenCompraProv.Estado.PENDIENTE:
            messages.error(request, "Esta solicitud ya fue resuelta.")
            return redirect("web_admin_solicitud_oc_prov_detalle", solicitud_id=sol.id)

        if accion == "rechazar":
            motivo = (request.POST.get("motivo_rechazo") or "").strip()
            try:
                rechazar_solicitud(sol.id, motivo=motivo)
                messages.success(request, "Solicitud rechazada. El empleado recibirá una notificación.")
            except ValueError as e:
                messages.error(request, str(e))
            return redirect("web_admin_solicitudes_oc_prov")

        if accion == "aprobar":
            try:
                proveedor_id = int(request.POST.get("proveedor_id") or 0)
                cantidad = int(request.POST.get("cantidad") or 0)
            except (TypeError, ValueError):
                messages.error(request, "Datos inválidos.")
                return redirect("web_admin_solicitud_oc_prov_detalle", solicitud_id=sol.id)
            if proveedor_id < 1 or cantidad < 1:
                messages.error(request, "Proveedor y cantidad son obligatorios.")
                return redirect("web_admin_solicitud_oc_prov_detalle", solicitud_id=sol.id)
            precio_unitario = _parse_costo_unitario(request.POST.get("precio_unitario"))
            if precio_unitario is None:
                messages.error(request, "Indica un costo unitario válido para aprobar la solicitud.")
                return redirect("web_admin_solicitud_oc_prov_detalle", solicitud_id=sol.id)
            if precio_unitario < 0:
                messages.error(request, "El costo unitario no puede ser negativo.")
                return redirect("web_admin_solicitud_oc_prov_detalle", solicitud_id=sol.id)
            try:
                sol, orden, cat_info = aprobar_y_generar_orden(
                    sol.id,
                    proveedor_id=proveedor_id,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                )
                msg = (
                    f"Solicitud aprobada. Orden de compra #{orden.id} creada. "
                    "El costo del producto en catálogo se actualizó con el valor aprobado."
                )
                if cat_info.get("precio_venta_actualizado") and cat_info.get("nuevo_precio_venta") is not None:
                    msg += (
                        f" Precio de venta recalculado (mismo margen sobre costo anterior): "
                        f"${cat_info['nuevo_precio_venta']}."
                    )
                msg += " El empleado fue notificado."
                messages.success(request, msg)
            except ValueError as e:
                messages.error(request, str(e))
            return redirect("web_admin_solicitudes_oc_prov")

    return render(
        request,
        "frontend/admin/solicitud_oc_prov_detalle.html",
        {
            "usuario": usuario,
            "solicitud": sol,
            "proveedores": proveedores,
        },
    )
