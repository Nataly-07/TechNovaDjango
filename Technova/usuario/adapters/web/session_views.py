"""
Vistas web con sesion (plantillas). Delegan autenticacion en el caso de uso de aplicacion.
"""

import logging

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
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
        "Cuenta creada. Revisa tu correo para confirmar tu identidad antes de finalizar una compra. "
        "Luego puedes iniciar sesión.",
    )
    return redirect("web_login")


@require_http_methods(["GET"])
def confirmar_correo_web(request: HttpRequest, token: str) -> HttpResponse:
    """Confirma el correo con el token enviado al registrarse."""
    token = (token or "").strip()
    if not token:
        messages.error(request, "El enlace no es válido.")
        return redirect("web_login")

    usuario = Usuario.objects.filter(token_verificacion_correo=token).first()
    if usuario is None:
        messages.error(request, "El enlace no es válido o ya fue usado.")
        return redirect("web_login")

    if usuario.token_verificacion_expira and usuario.token_verificacion_expira < timezone.now():
        messages.error(request, "Este enlace expiró. Contacta soporte o vuelve a registrarte.")
        return redirect("web_login")

    Usuario.objects.filter(pk=usuario.pk).update(
        correo_verificado=True,
        token_verificacion_correo="",
        token_verificacion_expira=None,
    )
    messages.success(request, "Correo confirmado. Ya puedes iniciar sesión y completar compras.")
    return redirect(f"{reverse('web_login')}?accountActivated=true")


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
    messages.success(request, "Sesion iniciada correctamente.")
    if usuario.rol == Usuario.Rol.ADMIN:
        return redirect("web_admin_perfil")
    if usuario.rol == Usuario.Rol.EMPLEADO:
        return redirect("web_empleado_inicio")
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
    request.session.flush()
    messages.info(request, "Sesion cerrada.")
    return redirect("web_login")
