from django.views.decorators.http import require_GET

from common.container import get_producto_service
from common.api import success_response


@require_GET
def listar_productos(request):
    service = get_producto_service()
    productos = service.listar_productos_activos()
    return success_response(
        {
            "items": [
                {
                    "id": producto.id,
                    "codigo": producto.codigo,
                    "nombre": producto.nombre,
                    "proveedor_id": producto.proveedor_id,
                    "stock": producto.stock,
                    "costo_unitario": str(producto.costo_unitario),
                }
                for producto in productos
            ]
        }
    )
