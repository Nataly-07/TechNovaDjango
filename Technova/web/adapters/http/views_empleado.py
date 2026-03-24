from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.application.use_cases.autenticacion_usecases import credenciales_coinciden
from usuario.infrastructure.models.usuario_model import Usuario

from web.domain.constants import EMPLEADO_SECCIONES
from web.adapters.http.decorators import empleado_login_required


@empleado_login_required
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
