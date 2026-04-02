from django.shortcuts import render
from web.adapters.http.decorators import admin_login_required

@admin_login_required
def admin_ordenes_compra_test(request):
    """Vista de prueba para diagnosticar problemas"""
    try:
        # Intentar importar los modelos
        from orden.infrastructure.models import OrdenCompra, DetalleOrden
        
        # Verificar que podemos acceder a los datos
        total_ordenes = OrdenCompra.objects.count()
        
        return render(request, 'frontend/admin/ordenes_compra_test.html', {
            'usuario': request.user,
            'total_ordenes': total_ordenes,
            'import_exitosa': True,
            'mensaje': f'Se encontraron {total_ordenes} órdenes en la base de datos'
        })
        
    except ImportError as e:
        return render(request, 'frontend/admin/ordenes_compra_test.html', {
            'usuario': request.user,
            'import_exitosa': False,
            'error': f'Error de importación: {str(e)}'
        })
    except Exception as e:
        return render(request, 'frontend/admin/ordenes_compra_test.html', {
            'usuario': request.user,
            'import_exitosa': True,
            'error': f'Error al acceder a los datos: {str(e)}'
        })
