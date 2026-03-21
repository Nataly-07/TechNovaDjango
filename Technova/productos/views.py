from django.views.decorators.http import require_GET

from common.api import success_response
from productos.application.services import ProductoService
from productos.infrastructure.repositories import ProductoOrmRepository


@require_GET
def listar_productos(request):
    service = ProductoService(ProductoOrmRepository())
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
