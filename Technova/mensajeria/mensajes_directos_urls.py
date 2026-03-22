from django.urls import path

from mensajeria.adapters.api.mensajes_directos_views import (
    crear_conversacion,
    detalle_mensaje_directo,
    estadisticas_mensajes_directos,
    marcar_leido_mensaje,
    mensajes_directos_raiz,
    mensajes_por_conversacion,
    mensajes_por_empleado,
    mensajes_por_usuario,
    responder_mensaje_directo,
)

urlpatterns = [
    path("estadisticas/", estadisticas_mensajes_directos, name="md_estadisticas"),
    path("conversacion/", crear_conversacion, name="md_crear_conversacion"),
    path(
        "conversacion/<str:conversation_id>/",
        mensajes_por_conversacion,
        name="md_por_conversacion",
    ),
    path("usuario/<int:user_id>/", mensajes_por_usuario, name="md_por_usuario"),
    path(
        "empleado/<int:empleado_id>/",
        mensajes_por_empleado,
        name="md_por_empleado",
    ),
    path(
        "<int:mensaje_id>/responder/",
        responder_mensaje_directo,
        name="md_responder",
    ),
    path(
        "<int:mensaje_id>/marcar-leido/",
        marcar_leido_mensaje,
        name="md_marcar_leido",
    ),
    path("<int:mensaje_id>/", detalle_mensaje_directo, name="md_detalle"),
    path("", mensajes_directos_raiz, name="md_raiz"),
]
