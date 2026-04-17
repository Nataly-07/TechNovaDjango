"""
Vistas web con sesion (plantillas). Delegan autenticacion en el caso de uso de aplicacion.
"""

import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from usuario.application.registro_usuario_service import registrar_usuario_desde_payload
from usuario.application.use_cases.autenticacion_usecases import autenticar_por_correo
from usuario.models import Usuario

SESSION_USUARIO_ID = "usuario_id"
SESSION_USUARIO_ROL = "usuario_rol"
logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
def registro_web(request: HttpRequest) -> HttpResponse:
    """Registro web (plantilla Spring); delega creacion en `registrar_usuario_desde_payload`."""
    if request.method == "GET":
        return render(request, "usuarios/registro.html", {})

    correo = (request.POST.get("correo") or "").strip().lower()
    confirmar = (request.POST.get("confirmar-correo") or "").strip().lower()
    password = request.POST.get("password") or ""
    password_confirmation = request.POST.get("password_confirmation") or ""

    if correo != confirmar:
        messages.error(request, "Los correos no coinciden.")
        return redirect("web_registro")
    if password != password_confirmation:
        messages.error(request, "Las contrasenas no coinciden.")
        return redirect("web_registro")

    payload = {
        "email": correo,
        "password": password,
        "firstName": (request.POST.get("nombre") or "").strip(),
        "lastName": (request.POST.get("apellido") or "").strip(),
        "documentType": (request.POST.get("tipo-doc") or "").strip(),
        "documentNumber": (request.POST.get("documento") or "").strip(),
        "phone": (request.POST.get("telefono") or "").strip(),
        "address": (request.POST.get("direccion") or "").strip(),
    }

    result = registrar_usuario_desde_payload(payload, admin_usuario=None)
    if result.error:
        messages.error(request, result.error)
        return redirect("web_registro")

    messages.success(
        request,
        "Cuenta creada correctamente. Te enviamos un correo de bienvenida. Ya puedes iniciar sesión.",
    )
    return redirect("web_login")


def _urls_api_usuario() -> dict[str, str]:
    """Rutas de la API y login web para el JavaScript de la plantilla (equivalente al front Spring)."""
    return {
        "verificar_estado": reverse("usuarios_verificar_estado"),
        "verificar_identidad": reverse("usuarios_verificar_identidad"),
        "activar_cuenta": reverse("usuarios_activar_cuenta"),
        "recuperar_contrasena": reverse("usuarios_recuperar_contrasena"),
        "web_login": reverse("web_login"),
    }


@require_http_methods(["GET", "POST"])
def login_web(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        if request.session.get(SESSION_USUARIO_ID):
            uid = request.session.get(SESSION_USUARIO_ID)
            try:
                u = Usuario.objects.get(pk=uid)
                if u.rol == Usuario.Rol.ADMIN:
                    return redirect("web_admin_perfil")
                if u.rol == Usuario.Rol.EMPLEADO:
                    return redirect("web_empleado_inicio")
            except Usuario.DoesNotExist:
                pass
            return redirect("inicio_autenticado")
        ctx = {
            "api_usuario": _urls_api_usuario(),
            "account_activated": request.GET.get("accountActivated") == "true",
            "account_deactivated_notice": request.GET.get("accountDeactivated") == "true",
            "next": (request.GET.get("next") or "").strip(),
        }
        return render(request, "usuarios/login.html", ctx)

    email = (request.POST.get("email") or "").strip().lower()
    password = request.POST.get("password") or ""

    if not email or not password:
        messages.error(request, "Credenciales invalidas.")
        return redirect("web_login")

    resultado = autenticar_por_correo(
        email, password, tratar_inactivo_como_credenciales_invalidas=False
    )
    if resultado.error == "inactivo":
        messages.error(request, "Cuenta inactiva.")
        return redirect("web_login")
    if resultado.usuario is None:
        messages.error(request, "Credenciales invalidas.")
        return redirect("web_login")

    usuario = resultado.usuario
    request.session[SESSION_USUARIO_ID] = usuario.id
    request.session[SESSION_USUARIO_ROL] = usuario.rol
    if usuario.rol == Usuario.Rol.CLIENTE:
        from web.application.guest_carrito import merge_guest_cart_into_user

        merge_guest_cart_into_user(request, usuario.id)
    messages.success(request, "Sesion iniciada correctamente.")
    if usuario.rol == Usuario.Rol.ADMIN:
        return redirect("web_admin_perfil")
    if usuario.rol == Usuario.Rol.EMPLEADO:
        return redirect("web_empleado_inicio")
    nxt = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if nxt.startswith("/") and not nxt.startswith("//"):
        return redirect(nxt)
    return redirect("inicio_autenticado")


@require_http_methods(["GET"])
def home_portal(request: HttpRequest) -> HttpResponse:
    """Pagina minima post-login hasta que existan mas plantillas."""
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return redirect("web_login")
    try:
        u = Usuario.objects.get(pk=uid)
        if u.rol == Usuario.Rol.EMPLEADO:
            return redirect("web_empleado_inicio")
    except Usuario.DoesNotExist:
        pass
    return render(
        request,
        "usuarios/home_portal.html",
        {
            "usuario_id": uid,
            "rol": request.session.get(SESSION_USUARIO_ROL),
        },
    )


@require_http_methods(["POST"])
def logout_web(request: HttpRequest) -> HttpResponse:
    # Descartar mensajes pendientes (p. ej. "Sesion iniciada...") antes de invalidar la sesión,
    # para que no reaparezcan en la siguiente pantalla (login).
    list(messages.get_messages(request))
    request.session.flush()
    messages.info(request, "Sesion cerrada.")
    return redirect("web_login")
