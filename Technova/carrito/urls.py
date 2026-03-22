from django.urls import path

from carrito.views import (
    actualizar_item_carrito,
    agregar_item_carrito,
    crear_carrito,
    crear_favorito,
    eliminar_favorito_usuario_producto,
    eliminar_item_carrito,
    items_carrito_por_usuario,
    listar_carritos,
    listar_favoritos,
    vaciar_carrito_usuario,
)

urlpatterns = [
    path(
        "favoritos/<int:usuario_id>/producto/<int:producto_id>/",
        eliminar_favorito_usuario_producto,
        name="eliminar_favorito",
    ),
    path("<int:usuario_id>/vaciar/", vaciar_carrito_usuario, name="vaciar_carrito_usuario"),
    path(
        "<int:usuario_id>/eliminar/<int:detalle_id>/",
        eliminar_item_carrito,
        name="eliminar_item_carrito",
    ),
    path("<int:usuario_id>/actualizar/", actualizar_item_carrito, name="actualizar_item_carrito"),
    path("<int:usuario_id>/agregar/", agregar_item_carrito, name="agregar_item_carrito"),
    path("<int:usuario_id>/", items_carrito_por_usuario, name="items_carrito_usuario"),
    path("", listar_carritos, name="listar_carritos"),
    path("crear/", crear_carrito, name="crear_carrito"),
    path("favoritos/", listar_favoritos, name="listar_favoritos"),
    path("favoritos/crear/", crear_favorito, name="crear_favorito"),
]
