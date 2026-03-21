from django.urls import path

from carrito.views import crear_carrito, crear_favorito, listar_carritos, listar_favoritos

urlpatterns = [
    path("", listar_carritos, name="listar_carritos"),
    path("crear/", crear_carrito, name="crear_carrito"),
    path("favoritos/", listar_favoritos, name="listar_favoritos"),
    path("favoritos/crear/", crear_favorito, name="crear_favorito"),
]
