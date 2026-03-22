from django.urls import path

from proveedor.views import catalogo_proveedores, patch_estado_proveedor, proveedor_por_id

urlpatterns = [
    path("<int:proveedor_id>/estado/", patch_estado_proveedor, name="proveedor_patch_estado"),
    path("<int:proveedor_id>/", proveedor_por_id, name="proveedor_por_id"),
    path("", catalogo_proveedores, name="catalogo_proveedores"),
]
