from django.urls import path

from carrito.adapters.api.favoritos_views import (
    favorito_usuario_producto,
    listar_favoritos_por_usuario,
    listar_todos_favoritos,
    toggle_favorito,
)

urlpatterns = [
    path(
        "usuario/<int:usuario_id>/producto/<int:producto_id>/toggle/",
        toggle_favorito,
        name="favoritos_toggle",
    ),
    path(
        "usuario/<int:usuario_id>/producto/<int:producto_id>/",
        favorito_usuario_producto,
        name="favoritos_usuario_producto",
    ),
    path("usuario/<int:usuario_id>/", listar_favoritos_por_usuario, name="favoritos_por_usuario"),
    path("", listar_todos_favoritos, name="favoritos_todos"),
]
