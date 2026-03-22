"""
Vistas web con sesion (plantillas). Delegan autenticacion en el caso de uso de aplicacion.
"""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from usuario.application.use_cases.autenticacion_usecases import autenticar_por_correo

SESSION_USUARIO_ID = "usuario_id"
SESSION_USUARIO_ROL = "usuario_rol"


def index_public(request: HttpRequest) -> HttpResponse:
    """Raiz publica: con sesion va al portal; si no, al login (hasta exista landing catalogo)."""
    if request.session.get(SESSION_USUARIO_ID):
        return redirect("home_portal")
    return redirect("web_login")


def registro_stub(request: HttpRequest) -> HttpResponse:
    """Reservado: plantilla de registro alineada al proyecto Spring."""
    return HttpResponse(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Registro</title></head>"
        "<body style='font-family:sans-serif;padding:2rem;'>"
        "<p>Registro: proximamente (misma vista que TechNova Java).</p>"
        "<p><a href='" + reverse("web_login") + "'>Volver al login</a></p>"
        "</body></html>",
        content_type="text/html; charset=utf-8",
    )


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
            return redirect("home_portal")
        ctx = {
            "api_usuario": _urls_api_usuario(),
            "account_activated": request.GET.get("accountActivated") == "true",
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
    return redirect("home_portal")


@require_http_methods(["GET"])
def home_portal(request: HttpRequest) -> HttpResponse:
    """Pagina minima post-login hasta que existan mas plantillas."""
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return redirect("web_login")
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
