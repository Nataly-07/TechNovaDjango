from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime
import json

# Importaciones directas de modelos
try:
    from orden.infrastructure.models import OrdenCompra, DetalleOrden
except ImportError:
    # Si falla la importación, intentar importación directa
    try:
        from orden.models import OrdenCompra, DetalleOrden
    except ImportError:
        OrdenCompra = None
        DetalleOrden = None

from proveedor.models import Proveedor
from producto.models import Producto

# Importar el decorador correcto del proyecto
from web.adapters.http.decorators import admin_login_required


def admin_usuario_sesion(request):
    """Función helper para obtener usuario de sesión"""
    return request.user


@admin_login_required
def admin_ordenes_compra(request):
    """Vista principal de Órdenes de Compra para el admin"""
    # Verificar que los modelos estén disponibles
    if OrdenCompra is None:
        return render(request, 'frontend/admin/error.html', {
            'error': 'El módulo de órdenes no está disponible. Contacte al administrador.',
            'usuario': request.user
        })
    
    try:
        usuario = admin_usuario_sesion(request)
        
        # Obtener parámetros de filtrado
        estado_filter = request.GET.get('estado', '')
        proveedor_filter = request.GET.get('proveedor', '')
        fecha_desde = request.GET.get('fecha_desde', '')
        fecha_hasta = request.GET.get('fecha_hasta', '')
        busqueda = request.GET.get('busqueda', '')
        
        # Query base de órdenes
        ordenes_query = OrdenCompra.objects.select_related('proveedor').prefetch_related('detalles__producto')
        
        # Aplicar filtros
        if estado_filter:
            ordenes_query = ordenes_query.filter(estado=estado_filter)
        
        if proveedor_filter:
            ordenes_query = ordenes_query.filter(proveedor_id=proveedor_filter)
        
        if fecha_desde:
            try:
                fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d').date()
                ordenes_query = ordenes_query.filter(fecha__gte=fecha_desde_dt)
            except ValueError:
                pass
        
        if fecha_hasta:
            try:
                fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d').date()
                ordenes_query = ordenes_query.filter(fecha__lte=fecha_hasta_dt)
            except ValueError:
                pass
        
        if busqueda:
            ordenes_query = ordenes_query.filter(
                Q(proveedor__nombre__icontains=busqueda) |
                Q(id__icontains=busqueda)
            )
        
        # Ordenar y obtener resultados
        ordenes = ordenes_query.order_by('-fecha', '-id')
        
        # Estadísticas
        stats = {
            'total_ordenes': ordenes.count(),
            'pendientes': ordenes.filter(estado='pendiente').count(),
            'recibidas': ordenes.filter(estado='recibida').count(),
            'canceladas': ordenes.filter(estado='cancelada').count(),
            'total_invertido': ordenes.aggregate(total=Sum('total'))['total'] or 0,
        }
        
        # Opciones para filtros
        proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
        estados = OrdenCompra.Estado.choices
        
        context = {
            'usuario': usuario,
            'ordenes': ordenes,
            'stats': stats,
            'proveedores': proveedores,
            'estados': estados,
            'filtros_actuales': {
                'estado': estado_filter,
                'proveedor': proveedor_filter,
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta,
                'busqueda': busqueda,
            }
        }
        
        return render(request, 'frontend/admin/ordenes_compra.html', context)
        
    except Exception as e:
        return render(request, 'frontend/admin/error.html', {
            'error': f'Error al cargar las órdenes: {str(e)}',
            'usuario': request.user
        })


@admin_login_required
def admin_orden_compra_detalle(request, orden_id):
    """Vista de detalle de una orden de compra específica"""
    usuario = admin_usuario_sesion(request)
    
    try:
        orden = OrdenCompra.objects.select_related('proveedor').prefetch_related(
            'detalles__producto'
        ).get(id=orden_id)
    except OrdenCompra.DoesNotExist:
        return render(request, 'frontend/admin/404.html', status=404)
    
    # Calcular estadísticas de la orden
    detalles_data = []
    for detalle in orden.detalles.all():
        detalles_data.append({
            'producto': detalle.producto,
            'cantidad': detalle.cantidad,
            'precio_unitario': detalle.precio_unitario,
            'subtotal': detalle.subtotal,
        })
    
    context = {
        'usuario': usuario,
        'orden': orden,
        'detalles': detalles_data,
        'estados_posibles': OrdenCompra.Estado.choices,
    }
    
    return render(request, 'frontend/admin/orden_compra_detalle.html', context)


@admin_login_required
@csrf_exempt
@require_POST
def admin_orden_compra_cambiar_estado(request, orden_id):
    """Cambiar estado de una orden de compra (AJAX)"""
    usuario = admin_usuario_sesion(request)
    
    try:
        orden = OrdenCompra.objects.get(id=orden_id)
        nuevo_estado = request.POST.get('estado')
        
        if nuevo_estado not in [choice[0] for choice in OrdenCompra.Estado.choices]:
            return JsonResponse({
                'success': False,
                'message': 'Estado no válido'
            }, status=400)
        
        # Cambiar estado
        orden.estado = nuevo_estado
        orden.save()
        
        # Si la orden se marca como recibida, actualizar stock de productos
        if nuevo_estado == OrdenCompra.Estado.RECIBIDA:
            for detalle in orden.detalles.all():
                producto = detalle.producto
                producto.stock += detalle.cantidad
                producto.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Estado actualizado a "{orden.get_estado_display()}" correctamente',
            'nuevo_estado_display': orden.get_estado_display(),
            'nuevo_estado': orden.estado
        })
        
    except OrdenCompra.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Orden no encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al actualizar estado: {str(e)}'
        }, status=500)


@admin_login_required
def admin_orden_compra_crear(request):
    """Vista para crear una nueva orden de compra"""
    usuario = admin_usuario_sesion(request)
    
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            proveedor_id = request.POST.get('proveedor')
            fecha = request.POST.get('fecha')
            estado = request.POST.get('estado', OrdenCompra.Estado.PENDIENTE)
            
            # Procesar detalles
            productos_data = json.loads(request.POST.get('productos_data', '[]'))
            
            if not productos_data:
                return JsonResponse({
                    'success': False,
                    'message': 'Debe agregar al menos un producto'
                }, status=400)
            
            # Crear orden
            orden = OrdenCompra.objects.create(
                proveedor_id=proveedor_id,
                fecha=fecha,
                estado=estado,
                total=0  # Se calculará después
            )
            
            # Crear detalles y calcular total
            total = 0
            for item in productos_data:
                producto = Producto.objects.get(id=item['producto_id'])
                cantidad = int(item['cantidad'])
                precio_unitario = float(item['precio_unitario'])
                subtotal = cantidad * precio_unitario
                
                DetalleOrden.objects.create(
                    orden_compra=orden,
                    producto=producto,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    subtotal=subtotal
                )
                
                total += subtotal
            
            # Actualizar total de la orden
            orden.total = total
            orden.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Orden de compra creada correctamente',
                'orden_id': orden.id,
                'redirect_url': f'/admin/ordenes-compra/{orden.id}/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al crear orden: {str(e)}'
            }, status=500)
    
    # GET - mostrar formulario
    proveedores = Proveedor.objects.filter(activo=True).order_by('nombre')
    productos = Producto.objects.filter(activo=True).order_by('nombre')
    
    context = {
        'usuario': usuario,
        'proveedores': proveedores,
        'productos': productos,
        'estados': OrdenCompra.Estado.choices,
        'fecha_actual': timezone.now().date().strftime('%Y-%m-%d'),
    }
    
    return render(request, 'frontend/admin/orden_compra_crear.html', context)


@admin_login_required
def admin_ordenes_compra_api(request):
    """API endpoint para obtener datos de órdenes (AJAX)"""
    usuario = admin_usuario_sesion(request)
    
    # Parámetros
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search = request.GET.get('search[value]', '')
    
    # Query base
    ordenes_query = OrdenCompra.objects.select_related('proveedor').prefetch_related('detalles')
    
    # Búsqueda
    if search:
        ordenes_query = ordenes_query.filter(
            Q(proveedor__nombre__icontains=search) |
            Q(id__icontains=search)
        )
    
    # Total records
    total_records = ordenes_query.count()
    
    # Paginación
    ordenes = ordenes_query.order_by('-fecha', '-id')[start:start + length]
    
    # Formatear datos
    data = []
    for orden in ordenes:
        data.append({
            'id': orden.id,
            'proveedor': orden.proveedor.nombre,
            'fecha': orden.fecha.strftime('%d/%m/%Y'),
            'total': float(orden.total),
            'estado': orden.estado,
            'estado_display': orden.get_estado_display(),
            'creado_en': orden.creado_en.strftime('%d/%m/%Y %H:%M'),
            'detalles_count': orden.detalles.count(),
        })
    
    response = {
        'draw': draw,
        'recordsTotal': total_records,
        'recordsFiltered': total_records,
        'data': data
    }
    
    return JsonResponse(response)
