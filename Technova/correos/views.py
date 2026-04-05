from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.mail import EmailMessage, EmailMultiAlternatives, get_connection
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from decimal import Decimal, InvalidOperation
import json
import logging

from web.adapters.http.decorators import admin_login_required
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.infrastructure.models.usuario_model import Usuario
from .models import HistorialEnvio, DestinatarioEnvio
from producto.models import Producto

logger = logging.getLogger(__name__)


def _usuario_sesion(request):
    """Obtiene el usuario autenticado por sesión propia de Technova."""
    uid = request.session.get(SESSION_USUARIO_ID)
    if not uid:
        return None
    try:
        return Usuario.objects.get(pk=uid)
    except Usuario.DoesNotExist:
        return None


def _decimal_desde_post(val):
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return Decimal(s.replace(",", "."))
    except InvalidOperation:
        return None


def _imagen_url_producto(producto: Producto) -> str:
    u = (getattr(producto, "imagen_url", None) or "").strip()
    if u:
        return u
    try:
        img = producto.imagenes.filter(activa=True).order_by("orden", "id").first()
        if img and img.url:
            return (img.url or "").strip()
    except Exception:
        pass
    return ""


def _url_absoluta_email(request, url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if u.startswith(("http://", "https://")):
        return u
    if u.startswith("/"):
        return request.build_absolute_uri(u)
    return u


@admin_login_required
@require_GET
def panel_correos(request):
    """
    Vista principal del módulo Correos
    """
    try:
        # Obtener usuarios para la tabla de selección
        usuarios = Usuario.objects.all().order_by('-id')
        
        # Estadísticas rápidas
        total_envios = HistorialEnvio.objects.count()
        envios_hoy = HistorialEnvio.objects.filter(
            fecha_envio__date=timezone.now().date()
        ).count()
        
        context = {
            'usuarios': usuarios,
            'total_envios': total_envios,
            'envios_hoy': envios_hoy,
            'usuario': _usuario_sesion(request),
        }
        
        return render(request, 'correos/panel_correos.html', context)
        
    except Exception as e:
        logger.error(f"Error en panel_correos: {e}")
        messages.error(request, f'Error al cargar el panel: {str(e)}')
        return redirect('web_admin_perfil')


@admin_login_required
@require_POST
def enviar_correos_masivos(request):
    """
    Procesar el envío masivo de correos
    """
    try:
        usuario_actual = _usuario_sesion(request)
        if usuario_actual is None:
            messages.error(request, 'Sesión expirada. Vuelve a iniciar sesión.')
            return redirect('web_login')

        # Validar datos del formulario
        asunto = request.POST.get('asunto', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        usuarios_seleccionados = request.POST.getlist('usuarios_seleccionados')
        
        if not asunto or not mensaje:
            messages.error(request, 'El asunto y el mensaje son obligatorios')
            return redirect('correos:panel_correos')
        
        if not usuarios_seleccionados:
            messages.error(request, 'Debes seleccionar al menos un destinatario')
            return redirect('correos:panel_correos')
        
        # Obtener usuarios seleccionados
        destinatarios = Usuario.objects.filter(id__in=usuarios_seleccionados)
        
        # Crear historial de envío
        with transaction.atomic():
            historial = HistorialEnvio.objects.create(
                asunto=asunto,
                cuerpo_mensaje=mensaje,
                total_destinatarios=len(destinatarios),
                tipo_envio='campana',
                autor=usuario_actual,
                ip_origen=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            # Crear registros de destinatarios
            destinatarios_envio = []
            for destinatario in destinatarios:
                destinatarios_envio.append(
                    DestinatarioEnvio(
                        historial=historial,
                        destinatario=destinatario,
                        email=destinatario.correo_electronico
                    )
                )
            
            DestinatarioEnvio.objects.bulk_create(destinatarios_envio)
        
        try:
            ok, fail = _procesar_envio_correos(historial)
            if fail == 0:
                messages.success(
                    request, f"Correo enviado correctamente a {ok} destinatario(s)."
                )
            elif ok == 0:
                messages.error(
                    request,
                    f"No se pudo enviar ningún correo ({fail} fallido(s)). Revisa el historial.",
                )
            else:
                messages.warning(
                    request,
                    f"Enviados {ok} correo(s); {fail} fallido(s). Revisa el historial.",
                )
        except Exception as e:
            logger.error(f"Error al enviar correos: {e}")
            historial.refresh_from_db()
            if historial.estado != "error":
                historial.estado = "error"
                historial.save(update_fields=["estado"])
            messages.error(request, f"Error al enviar correos: {str(e)}")
        
        return redirect('correos:panel_correos')
        
    except Exception as e:
        logger.error(f"Error en enviar_correos_masivos: {e}")
        messages.error(request, f'Error inesperado: {str(e)}')
        return redirect('correos:panel_correos')


@admin_login_required
@require_GET
def historial_envios(request):
    """
    Vista del historial de envíos realizados
    """
    try:
        envios = HistorialEnvio.objects.all().order_by('-fecha_envio')
        
        context = {
            'envios': envios,
            'usuario': _usuario_sesion(request),
        }
        
        return render(request, 'correos/historial_envios.html', context)
        
    except Exception as e:
        logger.error(f"Error en historial_envios: {e}")
        messages.error(request, f'Error al cargar historial: {str(e)}')
        return redirect('correos:panel_correos')


@admin_login_required
@require_GET
def modal_promocion_producto(request, producto_id):
    """
    Modal para promocionar un producto específico
    """
    try:
        producto = Producto.objects.get(id=producto_id)
        usuarios = Usuario.objects.all().order_by('-id')
        
        context = {
            'producto': producto,
            'usuarios': usuarios,
            'usuario': _usuario_sesion(request),
        }
        
        return render(request, 'correos/modal_promocion.html', context)
        
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Error en modal_promocion_producto: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@admin_login_required
@require_POST
def enviar_promocion_producto(request, producto_id):
    """
    Enviar promoción de un producto específico
    """
    try:
        usuario_actual = _usuario_sesion(request)
        if usuario_actual is None:
            return JsonResponse(
                {'success': False, 'message': 'Sesión expirada. Por favor, reingresa.'},
                status=401,
            )

        producto = Producto.objects.get(id=producto_id)
        asunto = request.POST.get('asunto', f'¡Promoción Especial: {producto.nombre}!')
        mensaje = request.POST.get('mensaje', '')
        mensaje_usuario = (request.POST.get('mensaje_usuario') or '').strip()
        usuarios_seleccionados = request.POST.getlist('usuarios_seleccionados')
        
        # CORRECCIÓN: Obtener y validar precios del formulario
        precio_promocion = request.POST.get('precio_promocion')
        precio_regular_post = _decimal_desde_post(request.POST.get('precio_regular'))
        fecha_fin_promocion_raw = request.POST.get('fecha_fin_promocion')
        
        # Validar que el precio de promoción sea válido
        if precio_promocion:
            try:
                precio_promocion = float(precio_promocion)
                if precio_promocion <= 0:
                    return JsonResponse({'error': 'El precio de promoción debe ser mayor a 0'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'El precio de promoción debe ser un número válido'}, status=400)
        
        if not usuarios_seleccionados:
            return JsonResponse({'error': 'Debes seleccionar al menos un destinatario'}, status=400)

        # Persistir promoción activa en el producto sin tocar el precio original
        if precio_promocion not in (None, ""):
            dt_fin = None
            if fecha_fin_promocion_raw:
                dt_fin = parse_datetime(fecha_fin_promocion_raw)
                if dt_fin is None:
                    return JsonResponse(
                        {'error': 'Fecha fin de promoción inválida.'}, status=400
                    )
                if timezone.is_naive(dt_fin):
                    dt_fin = timezone.make_aware(dt_fin, timezone.get_current_timezone())
                if dt_fin <= timezone.now():
                    return JsonResponse(
                        {'error': 'La fecha fin de promoción debe ser futura.'}, status=400
                    )
            producto.precio_promocion = precio_promocion
            producto.fecha_fin_promocion = dt_fin
            producto.save(update_fields=['precio_promocion', 'fecha_fin_promocion', 'actualizado_en'])
        
        # Precio regular: POST o fallback al precio base del producto (evita $0 cruzado)
        precio_regular_final = precio_regular_post
        if precio_regular_final is None or precio_regular_final <= 0:
            pb = producto.precio_base
            if pb is not None:
                precio_regular_final = Decimal(pb)
            else:
                precio_regular_final = Decimal("0")

        precio_promocion_dec = _decimal_desde_post(precio_promocion) if precio_promocion else None
        ahorro = Decimal("0")
        if precio_promocion_dec is not None and precio_regular_final is not None:
            diff = precio_regular_final - precio_promocion_dec
            if diff > 0:
                ahorro = diff

        imagen_raw = _imagen_url_producto(producto)
        imagen_absoluta = _url_absoluta_email(request, imagen_raw)

        # Generar mensaje HTML con información del producto y precios
        mensaje_html = render_to_string('correos/email_promocion.html', {
            'producto': producto,
            'mensaje_usuario': mensaje_usuario,
            'mensaje_sistema': mensaje,
            'asunto': asunto,
            'precio_promocion': float(precio_promocion_dec) if precio_promocion_dec is not None else None,
            'precio_regular': float(precio_regular_final),
            'ahorro': float(ahorro),
            'imagen_producto_url': imagen_absoluta,
        })
        
        # Crear historial de envío
        with transaction.atomic():
            historial = HistorialEnvio.objects.create(
                asunto=asunto,
                cuerpo_mensaje=mensaje_html,
                total_destinatarios=len(usuarios_seleccionados),
                tipo_envio='promocion',
                autor=usuario_actual,
                producto=producto,
                ip_origen=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            # Crear registros de destinatarios
            destinatarios = Usuario.objects.filter(id__in=usuarios_seleccionados)
            destinatarios_envio = []
            for destinatario in destinatarios:
                destinatarios_envio.append(
                    DestinatarioEnvio(
                        historial=historial,
                        destinatario=destinatario,
                        email=destinatario.correo_electronico  # CORREGIDO: campo correcto
                    )
                )
            
            DestinatarioEnvio.objects.bulk_create(destinatarios_envio)
        
        try:
            ok, fail = _procesar_envio_correos(historial, html_content=True)
            if ok == 0:
                return JsonResponse(
                    {
                        "success": False,
                        "error": "No se pudo enviar ningún correo. Revisa direcciones y el servidor SMTP.",
                    },
                    status=500,
                )
            msg = f"Promoción enviada a {ok} destinatario(s)."
            if fail:
                msg += f" {fail} fallido(s)."
            return JsonResponse({"success": True, "message": msg})
        except Exception as e:
            logger.error(f"Error al enviar promoción: {e}")
            historial.refresh_from_db()
            if historial.estado != "error":
                historial.estado = "error"
                historial.save(update_fields=["estado"])
            return JsonResponse({"error": f"Error al enviar: {str(e)}"}, status=500)
        
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Error en enviar_promocion_producto: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@admin_login_required
@require_GET
def filtrar_usuarios(request):
    """
    API para filtrar usuarios por rol
    """
    try:
        rol_filtro = request.GET.get('rol', '')
        
        if rol_filtro == 'clientes':
            usuarios = Usuario.objects.filter(rol='cliente').values('id', 'nombres', 'correo_electronico', 'rol')
        elif rol_filtro == 'empleados':
            usuarios = Usuario.objects.filter(rol='empleado').values('id', 'nombres', 'correo_electronico', 'rol')
        elif rol_filtro == 'admin':
            usuarios = Usuario.objects.filter(rol='admin').values('id', 'nombres', 'correo_electronico', 'rol')
        else:
            usuarios = Usuario.objects.all().values('id', 'nombres', 'correo_electronico', 'rol')
        
        return JsonResponse({'usuarios': list(usuarios)})
        
    except Exception as e:
        logger.error(f"Error en filtrar_usuarios: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def _correo_remitente_campanas():
    from django.conf import settings

    fe = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()
    if fe:
        return fe
    eh = (getattr(settings, "EMAIL_HOST_USER", None) or "").strip()
    return eh or "noreply@localhost"


def _correo_para_visible_campanas():
    """Lista para el encabezado To (tienda); destinatarios reales van en BCC."""
    from django.conf import settings

    v = getattr(settings, "TECHNOVA_BULK_MAIL_VISIBLE_TO", None)
    if v is None:
        v = ""
    else:
        v = str(v).strip()
    if not v:
        return []
    return [v]


def _procesar_envio_correos(historial, html_content=False):
    """
    Envía un correo por destinatario reutilizando una sola conexión SMTP.
    Los clientes van en BCC; en To solo el correo de la tienda (o vacío si así está configurado).
    Devuelve (enviados_ok, enviados_fallidos). Lanza solo si falla abrir la conexión.
    """
    historial.estado = "enviando"
    historial.enviados_exitosos = 0
    historial.enviados_fallidos = 0
    historial.save(update_fields=["estado", "enviados_exitosos", "enviados_fallidos"])

    destinatarios = list(historial.destinatarios.all())
    from_email = _correo_remitente_campanas()
    to_header = _correo_para_visible_campanas()

    connection = get_connection()
    try:
        connection.open()
    except Exception as exc:
        logger.exception("No se pudo abrir la conexión SMTP para el historial id=%s", historial.pk)
        for dest in destinatarios:
            dest.estado = "fallido"
            dest.error_message = str(exc)[:500]
            dest.fecha_envio = None
        if destinatarios:
            DestinatarioEnvio.objects.bulk_update(
                destinatarios, ["estado", "error_message", "fecha_envio"]
            )
        historial.enviados_exitosos = 0
        historial.enviados_fallidos = len(destinatarios)
        historial.estado = "error"
        historial.save(
            update_fields=[
                "estado",
                "enviados_exitosos",
                "enviados_fallidos",
            ]
        )
        raise

    exitosos = 0
    fallidos = 0
    try:
        for dest in destinatarios:
            email_addr = (dest.email or "").strip()
            if not email_addr:
                dest.estado = "fallido"
                dest.error_message = "Correo del destinatario vacío"
                dest.fecha_envio = None
                fallidos += 1
                continue
            try:
                if html_content:
                    alt_text = (
                        "Este mensaje está en HTML. Usa un cliente que permita HTML "
                        "para ver la promoción completa."
                    )
                    msg = EmailMultiAlternatives(
                        subject=historial.asunto,
                        body=alt_text,
                        from_email=from_email,
                        to=to_header,
                        bcc=[email_addr],
                        connection=connection,
                    )
                    msg.attach_alternative(historial.cuerpo_mensaje, "text/html")
                    msg.send()
                else:
                    msg = EmailMessage(
                        subject=historial.asunto,
                        body=historial.cuerpo_mensaje,
                        from_email=from_email,
                        to=to_header,
                        bcc=[email_addr],
                        connection=connection,
                    )
                    msg.send()
                dest.estado = "enviado"
                dest.fecha_envio = timezone.now()
                dest.error_message = None
                exitosos += 1
            except Exception as exc:
                logger.warning(
                    "Fallo envío a %s (historial id=%s): %s",
                    email_addr,
                    historial.pk,
                    exc,
                    exc_info=True,
                )
                dest.estado = "fallido"
                dest.error_message = str(exc)[:500]
                dest.fecha_envio = None
                fallidos += 1
    finally:
        try:
            connection.close()
        except Exception:
            logger.exception("Error al cerrar conexión SMTP (historial id=%s)", historial.pk)

    if destinatarios:
        DestinatarioEnvio.objects.bulk_update(
            destinatarios,
            ["estado", "fecha_envio", "error_message"],
        )

    historial.enviados_exitosos = exitosos
    historial.enviados_fallidos = fallidos
    if fallidos == 0:
        historial.estado = "completado"
    elif exitosos == 0:
        historial.estado = "error"
    else:
        historial.estado = "parcial"
    historial.save(
        update_fields=[
            "estado",
            "enviados_exitosos",
            "enviados_fallidos",
        ]
    )
    return exitosos, fallidos
