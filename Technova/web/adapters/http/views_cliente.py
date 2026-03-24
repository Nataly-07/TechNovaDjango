import json
from datetime import date

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST, require_http_methods

from carrito.models import Favorito
from common.container import get_carrito_lineas_service, get_carrito_query_service
from envio.models import Envio
from pago.models import MetodoPagoUsuario, Pago
from producto.models import Producto
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.application.use_cases.autenticacion_usecases import credenciales_coinciden
from usuario.infrastructure.models.usuario_model import Usuario
from venta.models import Venta

from web.application.request_helpers import wants_json_response
from web.adapters.http.decorators import cliente_login_required


@cliente_login_required
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


@cliente_login_required
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


@cliente_login_required
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


@cliente_login_required
@require_POST
def favorito_quitar(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    wants_json = wants_json_response(request)
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


@cliente_login_required
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


@cliente_login_required
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
