from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from producto.models import Producto
from web.application.admin_web_service import producto_modal_dict


@require_GET
def admin_producto_info(request, producto_id):
    """JSON con ficha del producto (promoción, modal Ver, etc.). Requiere sesión admin Technova."""
    session_usuario_id = request.session.get("usuario_id")
    if not session_usuario_id:
        return JsonResponse({"success": False, "error": "No autenticado"}, status=401)

    try:
        from usuario.models import Usuario

        usuario = Usuario.objects.get(pk=session_usuario_id)
    except Usuario.DoesNotExist:
        return JsonResponse({"success": False, "error": "Usuario no encontrado"}, status=401)

    if usuario.rol != "admin":
        return JsonResponse({"success": False, "error": "Permiso denegado"}, status=403)

    producto = get_object_or_404(
        Producto.objects.prefetch_related("imagenes"),
        pk=producto_id,
    )
    producto_data = producto_modal_dict(producto)

    return JsonResponse({"success": True, "producto": producto_data})


@login_required
@require_GET
def admin_producto_promocionar(request, producto_id):
    """Vista para mostrar el modal de promoción de producto (legado Django auth)."""
    try:
        if not request.user.rol == "admin":
            return JsonResponse({"error": "Permiso denegado"}, status=403)

        producto = get_object_or_404(Producto, pk=producto_id)

        from usuario.infrastructure.models.usuario_model import Usuario

        usuarios = Usuario.objects.all().order_by("-id")

        ctx = {
            "usuario": request.user,
            "producto": producto,
            "usuarios": usuarios,
        }

        return render(request, "frontend/admin/modal_promocion_simple.html", ctx)

    except Exception as e:
        messages.error(request, f"Error al cargar modal de promoción: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
