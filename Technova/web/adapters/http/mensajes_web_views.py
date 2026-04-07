"""
Módulo Mensajes (SSR) alineado con TechNovaJavaSpringBoot:
/admin/mensajes, /empleado/mensajes, /cliente/mensajes, POST /api/mensajes-empleado
"""

from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from common.container import get_atencion_query_service, get_mensajeria_query_service
from mensajeria.infrastructure.realtime_mensajes import broadcast_mensajes_event
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.models import Usuario


def _session_usuario(request) -> Usuario | None:
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return None
    return Usuario.objects.filter(pk=uid).first()


def _json_error(message: str, status: int) -> JsonResponse:
    return JsonResponse({"ok": False, "message": message}, status=status)


def _parse_json(request) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body.decode("utf-8"))


@require_GET
def admin_mensajes_page(request):
    u = _session_usuario(request)
    if u is None:
        return redirect("web_login")
    if u.rol != Usuario.Rol.ADMIN:
        return redirect("inicio_autenticado")
    raw = request.GET.get("conversacionId")
    conversacion_id = None
    if raw is not None and str(raw).strip() != "":
        try:
            conversacion_id = int(raw)
        except (TypeError, ValueError):
            conversacion_id = None
    ctx = get_mensajeria_query_service().admin_mensajes_ssr_context(
        conversacion_id=conversacion_id,
        marcar_leidos=conversacion_id is not None,
        admin_usuario_id=u.id,
    )
    ctx["usuario"] = u
    return render(request, "frontend/admin/mensajes.html", ctx)


@require_GET
def empleado_mensajes_page(request):
    u = _session_usuario(request)
    if u is None:
        return redirect("web_login")
    if u.rol != Usuario.Rol.EMPLEADO:
        return redirect("inicio_autenticado")
    raw = request.GET.get("conversacionId")
    conversacion_admin_id = None
    if raw is not None and str(raw).strip() != "":
        try:
            conversacion_admin_id = int(raw)
        except (TypeError, ValueError):
            conversacion_admin_id = None
    ctx = get_mensajeria_query_service().empleado_mensajes_ssr_context(
        empleado_id=u.id,
        conversacion_admin_id=conversacion_admin_id,
        marcar_leidos=conversacion_admin_id is not None,
    )
    ctx["usuario"] = u
    ctx["seccion"] = "mensajes"
    return render(request, "frontend/empleado/mensajes.html", ctx)


@require_GET
def cliente_mensajes_page(request):
    u = _session_usuario(request)
    if u is None:
        return redirect("web_login")
    if u.rol != Usuario.Rol.CLIENTE:
        return redirect("inicio_autenticado")
    conv = (request.GET.get("conversationId") or "").strip() or None
    ctx = get_mensajeria_query_service().cliente_mensajes_ssr_context(
        usuario_id=u.id, conversacion_id=conv
    )
    ctx["usuario"] = u
    return render(request, "frontend/cliente/mensajes_cliente.html", ctx)


@require_http_methods(["POST"])
def cliente_mensajes_nueva_conversacion(request):
    u = _session_usuario(request)
    if u is None:
        return redirect("web_login")
    if u.rol != Usuario.Rol.CLIENTE:
        return redirect("inicio_autenticado")
    asunto = (request.POST.get("asunto") or "").strip()
    texto = (request.POST.get("mensaje") or "").strip()
    prioridad = (request.POST.get("prioridad") or "normal").strip().lower()
    if not asunto or not texto:
        from django.contrib import messages

        messages.error(request, "Completa asunto y mensaje.")
        return redirect("web_cliente_mensajes")
    svc = get_mensajeria_query_service()
    data = svc.crear_conversacion_inicial(u.id, asunto, texto, prioridad)
    cid = (data or {}).get("conversationId") or ""
    if cid:
        return redirect(f"/cliente/mensajes/?conversationId={cid}")
    return redirect("web_cliente_mensajes")


@require_http_methods(["POST"])
def cliente_mensajes_responder(request):
    u = _session_usuario(request)
    if u is None:
        return redirect("web_login")
    if u.rol != Usuario.Rol.CLIENTE:
        return redirect("inicio_autenticado")
    padre_id = request.POST.get("mensaje_padre_id")
    texto = (request.POST.get("mensaje") or "").strip()
    conv = (request.POST.get("conversationId") or "").strip()
    svc = get_mensajeria_query_service()
    pid: int | None = None
    try:
        if padre_id is not None and str(padre_id).strip() != "":
            pid = int(padre_id)
    except (TypeError, ValueError):
        pid = None
    if pid is None and conv:
        hilos = svc.listar_mensajes_por_conversacion(conv) or []
        if hilos:
            pid = int(hilos[-1]["id"])
    if pid is None:
        from django.contrib import messages

        messages.error(request, "No se pudo responder en este hilo.")
        return redirect("web_cliente_mensajes")
    if not texto:
        from django.contrib import messages

        messages.error(request, "Escribe un mensaje.")
        return redirect(f"/cliente/mensajes/?conversationId={conv}" if conv else "web_cliente_mensajes")
    svc.responder_mensaje_directo(pid, u.id, "cliente", texto)
    if conv:
        return redirect(f"/cliente/mensajes/?conversationId={conv}")
    return redirect("web_cliente_mensajes")


@csrf_protect
@require_POST
def api_mensajes_empleado_spring(request):
    u = _session_usuario(request)
    if u is None:
        return _json_error("No autenticado.", 401)
    try:
        body = _parse_json(request)
    except json.JSONDecodeError:
        return _json_error("JSON invalido.", 400)
    try:
        empleado_id = int(body.get("empleadoId"))
        remitente_id = int(body.get("remitenteId"))
    except (TypeError, ValueError):
        return _json_error("empleadoId y remitenteId requeridos.", 400)
    tipo_raw = (body.get("tipoRemitente") or "").strip().lower()
    asunto = (body.get("asunto") or "").strip() or "Mensaje"
    mensaje = (body.get("mensaje") or "").strip()
    if not mensaje:
        return _json_error("El mensaje no puede estar vacio.", 400)
    tipo_m = (body.get("tipo") or "general").strip()[:50] or "general"
    prioridad = (body.get("prioridad") or "normal").strip().lower()
    svc = get_mensajeria_query_service()
    if tipo_raw == "admin":
        if u.rol != Usuario.Rol.ADMIN:
            return _json_error("No autorizado.", 403)
        if remitente_id != u.id:
            return _json_error("remitenteId debe ser el administrador.", 400)
        msg = svc.crear_mensaje_staff_chat(
            empleado_usuario_id=empleado_id,
            remitente_usuario_id=u.id,
            tipo_remitente="admin",
            asunto=asunto[:200],
            mensaje=mensaje,
            tipo_mensaje=tipo_m,
            reclamo_id=None,
            prioridad=prioridad,
        )
    elif tipo_raw == "empleado":
        if u.rol != Usuario.Rol.EMPLEADO:
            return _json_error("No autorizado.", 403)
        if empleado_id != u.id:
            return _json_error("empleadoId no coincide con la sesion.", 400)
        msg = svc.crear_mensaje_staff_chat(
            empleado_usuario_id=u.id,
            remitente_usuario_id=u.id,
            tipo_remitente="empleado",
            asunto=asunto[:200],
            mensaje=mensaje,
            tipo_mensaje=tipo_m,
            reclamo_id=None,
            prioridad=prioridad,
        )
    else:
        return _json_error("tipoRemitente invalido.", 400)
    if msg is None:
        return _json_error("No se pudo crear el mensaje.", 400)
    broadcast_mensajes_event(empleado_id, {"event": "new_message", "message": msg})
    out = {"ok": True, **msg}
    return JsonResponse(out)


@require_GET
def admin_reclamos_gestion(request):
    u = _session_usuario(request)
    if u is None:
        return redirect("web_login")
    if u.rol != Usuario.Rol.ADMIN:
        return redirect("inicio_autenticado")
    reclamos_raw = get_atencion_query_service().listar_reclamos(None) or []
    empleados = list(
        Usuario.objects.filter(rol=Usuario.Rol.EMPLEADO, activo=True).order_by("nombres", "id")[:500]
    )
    return render(
        request,
        "frontend/admin/reclamos_gestion.html",
        {"usuario": u, "reclamos": reclamos_raw, "empleados": empleados},
    )


@require_http_methods(["POST"])
def admin_reclamos_asignar_sesion(request, reclamo_id: int):
    u = _session_usuario(request)
    if u is None:
        return redirect("web_login")
    if u.rol != Usuario.Rol.ADMIN:
        return redirect("inicio_autenticado")
    try:
        empleado_id = int(request.POST.get("empleado_usuario_id") or "")
    except (TypeError, ValueError):
        from django.contrib import messages
        from django.shortcuts import redirect

        messages.error(request, "Selecciona un empleado valido.")
        return redirect("web_admin_reclamos")
    data = get_atencion_query_service().asignar_reclamo_a_empleado(
        reclamo_id,
        empleado_id,
        admin_usuario_id=u.id,
    )
    from django.contrib import messages
    from django.shortcuts import redirect

    if data is None:
        messages.error(request, "No se pudo asignar el reclamo.")
    else:
        messages.success(
            request,
            f"Reclamo #{reclamo_id} asignado. Se notifico al empleado en Mensajes.",
        )
    return redirect("web_admin_reclamos")


@require_GET
def admin_mensajes_reclamo_json(request, reclamo_id: int):
    u = _session_usuario(request)
    if u is None or u.rol != Usuario.Rol.ADMIN:
        return JsonResponse({"error": "No autorizado"}, status=403)
    data = get_atencion_query_service().reclamo_a_dict(reclamo_id)
    if data is None:
        return JsonResponse({"error": "No encontrado"}, status=404)
    return JsonResponse(data)
