from django.urls import path

from producto.views import (
    buscar_productos,
    buscar_productos_avanzado,
    catalogo_productos,
    patch_estado_producto,
    producto_por_id,
    productos_por_categoria,
    productos_por_marca,
    productos_por_precio,
)

urlpatterns = [
    path("buscar-avanzado/", buscar_productos_avanzado, name="productos_buscar_avanzado"),
    path("precio/", productos_por_precio, name="productos_por_precio"),
    path("buscar/", buscar_productos, name="productos_buscar"),
    path("marca/<str:marca>/", productos_por_marca, name="productos_por_marca"),
    path("categoria/<str:categoria>/", productos_por_categoria, name="productos_por_categoria"),
    path("<int:producto_id>/estado/", patch_estado_producto, name="producto_patch_estado"),
    path("<int:producto_id>/", producto_por_id, name="producto_por_id"),
    path("", catalogo_productos, name="catalogo_productos"),
]
