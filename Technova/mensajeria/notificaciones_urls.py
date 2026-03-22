from django.urls import path

from mensajeria.adapters.api.notificaciones_views import (
    notificaciones_por_usuario_leida,
    notificaciones_por_usuario_rango,
    notificaciones_por_usuario,
    notificaciones_raiz,
)

urlpatterns = [
    path(
        "usuario/<int:user_id>/rango/",
        notificaciones_por_usuario_rango,
        name="notif_usuario_rango",
    ),
    path(
        "usuario/<int:user_id>/leida/",
        notificaciones_por_usuario_leida,
        name="notif_usuario_leida",
    ),
    path(
        "usuario/<int:user_id>/",
        notificaciones_por_usuario,
        name="notif_usuario",
    ),
    path("", notificaciones_raiz, name="notif_raiz"),
]
