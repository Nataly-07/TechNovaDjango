from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.mail import send_mail, send_mass_mail, get_connection
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
        
        # Enviar correos en segundo plano o sincrónicamente
        try:
            _procesar_envio_correos(historial)
            messages.success(request, f'Correo enviado exitosamente a {len(destinatarios)} destinatarios')
        except Exception as e:
            logger.error(f"Error al enviar correos: {e}")
            historial.estado = 'error'
            historial.save()
            messages.error(request, f'Error al enviar correos: {str(e)}')
        
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
        
        # Enviar correos
        try:
            _procesar_envio_correos(historial, html_content=True)
            return JsonResponse({
                'success': True, 
                'message': f'Promoción enviada a {len(destinatarios)} destinatarios'
            })
        except Exception as e:
            logger.error(f"Error al enviar promoción: {e}")
            historial.estado = 'error'
            historial.save()
            return JsonResponse({'error': f'Error al enviar: {str(e)}'}, status=500)
        
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


def _procesar_envio_correos(historial, html_content=False):
    """
    Función interna para procesar el envío de correos
    """
    from django.conf import settings
    import os
    
    # Actualizar estado a enviando
    historial.estado = 'enviando'
    historial.save()
    
    try:
        # Preparar datos para envío masivo
        destinatarios = historial.destinatarios.all()
        
        # Usar send_mass_mail para mejor rendimiento
        messages_data = []
        
        for dest in destinatarios:
            if html_content:
                # Para HTML, usamos send_mail individual
                send_mail(
                    subject=historial.asunto,
                    message='',  # Mensaje plano vacío
                    html_message=historial.cuerpo_mensaje,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[dest.email],
                    fail_silently=False,
                )
                dest.estado = 'enviado'
                dest.fecha_envio = timezone.now()
                historial.enviados_exitosos += 1
            else:
                # Para texto plano, preparamos para send_mass_mail
                messages_data.append((
                    historial.asunto,
                    historial.cuerpo_mensaje,
                    settings.DEFAULT_FROM_EMAIL,
                    [dest.email]
                ))
                dest.estado = 'enviado'
                dest.fecha_envio = timezone.now()
                historial.enviados_exitosos += 1
        
        if not html_content and messages_data:
            # Envío masivo para texto plano
            send_mass_mail(messages_data, fail_silently=False)
        
        # Actualizar estados
        destinatarios.bulk_update(
            destinatarios, 
            ['estado', 'fecha_envio']
        )
        
        # Actualizar historial
        if historial.enviados_fallidos == 0:
            historial.estado = 'completado'
        else:
            historial.estado = 'parcial'
        
        historial.save()
        
    except Exception as e:
        logger.error(f"Error en _procesar_envio_correos: {e}")
        historial.estado = 'error'
        historial.enviados_fallidos = historial.total_destinatarios - historial.enviados_exitosos
        historial.save()
        raise
