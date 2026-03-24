import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from carrito.models import Favorito
from common.container import get_carrito_lineas_service, get_carrito_query_service
from producto.models import Producto
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.infrastructure.models.usuario_model import Usuario

from web.application.catalogo_publico_service import (
    listas_categorias_marcas_publicas,
    producto_card_ctx,
)
from web.adapters.http.decorators import cliente_login_required


def index_public(request):
    """Landing pública (invitado): catálogo, ofertas y enlaces a login/registro (`/`)."""
    productos_qs = Producto.objects.filter(activo=True).order_by("id")
    productos_cards = [producto_card_ctx(p) for p in productos_qs[:24]]
    recientes_qs = Producto.objects.filter(activo=True).order_by("-creado_en", "-id")[:6]
    productos_recientes = [producto_card_ctx(p) for p in recientes_qs]
    categorias, marcas = listas_categorias_marcas_publicas()
    oferta_dia = productos_cards[0] if productos_cards else None
    ofertas_interes = productos_cards[:3]
    return render(
        request,
        "frontend/index_public.html",
        {
            "productos": productos_cards,
            "productos_recientes": productos_recientes,
            "categorias": categorias,
            "marcas": marcas,
            "oferta_dia": oferta_dia,
            "ofertas_interes": ofertas_interes,
        },
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


@cliente_login_required
def home(request):
    """Inicio autenticado / catálogo (`/inicio/`)."""
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
    return render(
        request,
        "frontend/cliente/home.html",
        {
            "usuario_id": uid,
            "favoritos_preview": favoritos_preview,
            "carrito_preview": carrito_preview,
        },
    )


@cliente_login_required
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
    return JsonResponse(
        {
            "ok": True,
            "message": "Producto agregado al carrito.",
            "carrito_preview": carrito_preview,
        }
    )


@cliente_login_required
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
