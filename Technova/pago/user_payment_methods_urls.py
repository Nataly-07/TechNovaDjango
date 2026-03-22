from django.urls import path

from pago.adapters.api.user_payment_methods_views import (
    listar_todos_metodos_usuario,
    metodos_usuario,
)

urlpatterns = [
    path("usuario/<int:usuario_id>/", metodos_usuario, name="upm_usuario"),
    path("", listar_todos_metodos_usuario, name="upm_todos"),
]
