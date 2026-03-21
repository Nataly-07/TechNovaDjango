from django.urls import path

from mensajeria.views import (
    crear_mensaje_directo,
    crear_mensaje_empleado,
    crear_notificacion,
    listar_mensajes_directos,
    listar_mensajes_empleado,
    listar_notificaciones,
)

urlpatterns = [
    path("notificaciones/", listar_notificaciones, name="listar_notificaciones"),
    path("notificaciones/crear/", crear_notificacion, name="crear_notificacion"),
    path("mensajes-directos/", listar_mensajes_directos, name="listar_mensajes_directos"),
    path("mensajes-directos/crear/", crear_mensaje_directo, name="crear_mensaje_directo"),
    path("mensajes-empleado/", listar_mensajes_empleado, name="listar_mensajes_empleado"),
    path("mensajes-empleado/crear/", crear_mensaje_empleado, name="crear_mensaje_empleado"),
]
