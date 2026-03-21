from django.urls import path

from productos.views import listar_productos

urlpatterns = [
    path("", listar_productos, name="listar_productos"),
]
