from django.urls import path

from atencion_cliente.views import (
    crear_reclamo,
    crear_solicitud,
    listar_reclamos,
    listar_solicitudes,
)

urlpatterns = [
    path("solicitudes/", listar_solicitudes, name="listar_solicitudes"),
    path("solicitudes/crear/", crear_solicitud, name="crear_solicitud"),
    path("reclamos/", listar_reclamos, name="listar_reclamos"),
    path("reclamos/crear/", crear_reclamo, name="crear_reclamo"),
]
