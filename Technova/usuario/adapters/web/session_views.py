"""
Vistas web con sesion (plantillas). Delegan autenticacion en el caso de uso de aplicacion.
"""

import logging
from email.mime.image import MIMEImage
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from usuario.application.registro_usuario_service import registrar_usuario_desde_payload
from usuario.application.use_cases.autenticacion_usecases import autenticar_por_correo
from usuario.models import Usuario

SESSION_USUARIO_ID = "usuario_id"
SESSION_USUARIO_ROL = "usuario_rol"
logger = logging.getLogger(__name__)


def _adjuntar_logo_cid(msg: EmailMultiAlternatives) -> None:
    """
    Adjunta logo inline por CID para entorno local.
    """
    candidatos = [
        Path(
            "C:/Users/Marcela/.cursor/projects/d-Nataly-DjangoVI-TechNovaDjango/assets/"
            "c__Users_Marcela_AppData_Roaming_Cursor_User_workspaceStorage_6fe0e0b928196acd4af263defd0b8f41_images_"
            "image-f2ee58ae-53aa-485a-9edd-3ef89852adfe.png"
        ),
        Path(
            "C:/Users/Marcela/.cursor/projects/d-Nataly-DjangoVI-TechNovaDjango/assets/"
            "c__Users_Marcela_AppData_Roaming_Cursor_User_workspaceStorage_6fe0e0b928196acd4af263defd0b8f41_images_"
            "image-56fb4712-af6f-4358-9bdb-fc0b62b35529.png"
        ),
        Path(
            "C:/Users/Marcela/.cursor/projects/d-Nataly-DjangoVI-TechNovaDjango/assets/"
            "c__Users_Marcela_AppData_Roaming_Cursor_User_workspaceStorage_6fe0e0b928196acd4af263defd0b8f41_images_"
            "image-fb336cc0-7a1c-4878-aeb6-9fc5a2941b48.png"
        ),
    ]
    logo_path = next((p for p in candidatos if p.exists()), None)
    if logo_path is None:
        return
    logo = MIMEImage(logo_path.read_bytes(), _subtype="png")
    logo.add_header("Content-ID", "<logo_technova>")
    logo.add_header("Content-Disposition", "inline")
    msg.attach(logo)


def _enviar_bienvenida_registro_web(request: HttpRequest, usuario: Usuario) -> None:
    """
    Envia correo de bienvenida sin interrumpir el flujo de registro.
    """
    try:
        correo = (getattr(usuario, "correo_electronico", None) or "").strip()
        if not correo:
            return

        asunto = f"¡Bienvenido a Technova, {usuario.nombres}!"
        tienda_url = request.build_absolute_uri("/")
        html = render_to_string(
            "correos/email_bienvenida.html",
            {
                "usuario": usuario,
                "nombre_usuario": usuario.nombres,
                "tienda_url": tienda_url,
            },
            request=request,
        )
        msg = EmailMultiAlternatives(
            subject=asunto,
            body="Bienvenido a Technova. Tu cuenta fue creada con éxito.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[correo],
        )
        msg.attach_alternative(html, "text/html")
        _adjuntar_logo_cid(msg)
        msg.send(fail_silently=False)
    except Exception:
        logger.exception(
            "No se pudo enviar correo de bienvenida para usuario_id=%s",
            getattr(usuario, "id", None),
        )


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

    _enviar_bienvenida_registro_web(request, result.usuario)
    messages.success(request, "Cuenta creada correctamente. Ya puedes iniciar sesion.")
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
