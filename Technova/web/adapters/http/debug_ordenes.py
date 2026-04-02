from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib import messages

from web.adapters.http.decorators import admin_login_required
from orden.application.orden_compra_service import OrdenCompraService


@require_GET
def debug_ordenes(request):
    """Vista de depuración para ver qué está pasando"""
    
    # Verificar sesión
    session_data = dict(request.session)
    
    # Verificar usuario autenticado
    usuario = getattr(request, 'user', None)
    
    # Verificar datos del servicio
    try:
        service = OrdenCompraService()
        ordenes = service.listar_ordenes()
        service_status = "OK"
        ordenes_count = len(ordenes)
    except Exception as e:
        service_status = f"ERROR: {str(e)}"
        ordenes_count = 0
    
    context = {
        'session_data': session_data,
        'usuario': usuario,
        'usuario_is_authenticated': usuario.is_authenticated if usuario else False,
        'service_status': service_status,
        'ordenes_count': ordenes_count,
    }
    
    return render(request, 'debug_ordenes.html', context)


@admin_login_required
@require_GET
def debug_ordenes_auth(request):
    """Vista de depuración con autenticación requerida"""
    
    # Verificar sesión después del decorador
    session_data = dict(request.session)
    
    # Verificar usuario autenticado
    usuario = getattr(request, 'user', None)
    
    # Verificar datos del servicio
    try:
        service = OrdenCompraService()
        ordenes = service.listar_ordenes()
        service_status = "OK"
        ordenes_count = len(ordenes)
    except Exception as e:
        service_status = f"ERROR: {str(e)}"
        ordenes_count = 0
    
    context = {
        'session_data': session_data,
        'usuario': usuario,
        'usuario_is_authenticated': usuario.is_authenticated if usuario else False,
        'service_status': service_status,
        'ordenes_count': ordenes_count,
    }
    
    return render(request, 'debug_ordenes.html', context)
