from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from producto.models import Producto
from web.application.admin_web_service import producto_modal_dict
from django.contrib import messages
import json

@require_GET  # ✅ SIN @login_required para evitar redirección
def admin_producto_info(request, producto_id):
    """API para obtener información de un producto específico"""
    try:
        # DEBUG: Imprimir información de autenticación
        print(f"=== DEBUG ADMIN_PRODUCTO_INFO ===")
        print(f"Usuario autenticado (Django): {request.user.is_authenticated}")
        print(f"Usuario (Django): {request.user}")
        print(f"User ID (Django): {getattr(request.user, 'id', 'None')}")
        print(f"Session key: {request.session.session_key}")
        
        # DEBUG: Revisar sesión personalizada de Technova
        session_usuario_id = request.session.get('usuario_id')
        session_usuario_rol = request.session.get('usuario_rol')
        print(f"Session usuario_id: {session_usuario_id}")
        print(f"Session usuario_rol: {session_usuario_rol}")
        
        # ✅ USAR AUTENTICACIÓN PERSONALIZADA DE TECHNOVA
        if not session_usuario_id:
            print("❌ No hay usuario_id en sesión")
            return JsonResponse({
                'success': False,
                'error': 'No autenticado'
            }, status=401)
        
        # Obtener usuario desde sesión
        try:
            from usuario.models import Usuario
            usuario = Usuario.objects.get(pk=session_usuario_id)
            print(f"✅ Usuario encontrado: {usuario}")
            print(f"✅ Rol del usuario: {usuario.rol}")
        except Usuario.DoesNotExist:
            print("❌ Usuario no encontrado en BD")
            return JsonResponse({
                'success': False,
                'error': 'Usuario no encontrado'
            }, status=401)
        
        # Verificar que sea admin
        if usuario.rol != 'admin':
            print("❌ Usuario no es admin")
            return JsonResponse({
                'success': False,
                'error': 'Permiso denegado'
            }, status=403)
        
        print("✅ Usuario autenticado y es admin")
        producto = get_object_or_404(Producto, pk=producto_id)
        
        # Usar la misma función que genera el JSON para el modal
        producto_data = producto_modal_dict(producto)
        
        return JsonResponse({
            'success': True,
            'producto': producto_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_GET
def admin_producto_promocionar(request, producto_id):
    """Vista para mostrar el modal de promoción de producto"""
    try:
        # Verificar que sea admin (CORREGIDO)
        if not request.user.rol == 'admin':
            return JsonResponse({"error": "Permiso denegado"}, status=403)
            
        producto = get_object_or_404(Producto, pk=producto_id)
        
        # Obtener usuarios para selección
        from usuario.infrastructure.models.usuario_model import Usuario
        usuarios = Usuario.objects.all().order_by('-id')
        
        ctx = {
            "usuario": request.user,
            "producto": producto,
            "usuarios": usuarios,
        }
        
        return render(request, "frontend/admin/modal_promocion_simple.html", ctx)
        
    except Exception as e:
        messages.error(request, f"Error al cargar modal de promoción: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
