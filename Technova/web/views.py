from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.application.use_cases.autenticacion_usecases import credenciales_coinciden
from usuario.infrastructure.models.usuario_model import Usuario


def _cliente_login_required(view_func):
    """Solo usuarios con sesión Django (misma clave que login_web)."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get(SESSION_USUARIO_ID):
            return redirect("web_login")
        return view_func(request, *args, **kwargs)

    return _wrapped


def root_entry(request):
    """Raíz `/`: con sesión → inicio autenticado; sin sesión → login."""
    if request.session.get(SESSION_USUARIO_ID):
        return redirect("inicio_autenticado")
    return redirect("web_login")


@_cliente_login_required
def home(request):
    """Inicio autenticado / catálogo (`/inicio/`)."""
    return render(request, "frontend/cliente/home.html")


@_cliente_login_required
def perfil_cliente(request):
    uid = request.session.get(SESSION_USUARIO_ID)
    usuario = None
    if uid:
        try:
            usuario = Usuario.objects.get(pk=uid)
        except Usuario.DoesNotExist:
            usuario = None
    ctx = {
        "usuario": usuario,
        "favoritos_count": 0,
        "carrito_count": 0,
        "pedidos_count": 0,
        "notificaciones_count": 0,
        "medios_pago_count": 0,
        "compras_count": 0,
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
    return render(request, "frontend/cliente/favoritos.html")


@_cliente_login_required
def notificaciones_cliente(request):
    return render(request, "frontend/cliente/notificaciones.html")


@_cliente_login_required
def carrito_page(request):
    return render(request, "frontend/cliente/carrito.html")


@_cliente_login_required
def pedidos_cliente(request):
    """Pedidos = ventas del usuario (ruta Java: /cliente/pedidos)."""
    return render(request, "frontend/cliente/pedidos.html")


@_cliente_login_required
def mis_compras(request):
    return render(request, "frontend/cliente/mis_compras.html")


@_cliente_login_required
def atencion_cliente(request):
    return render(request, "frontend/cliente/atencion.html")


@_cliente_login_required
def producto_detalle(request, producto_id: int):
    return render(request, "frontend/cliente/producto_detalle.html", {"producto_id": producto_id})
