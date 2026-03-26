from django.urls import path

from atencion_cliente.views import (
    crear_reclamo,
    crear_solicitud,
    listar_reclamos,
    listar_solicitudes,
)
from atencion_cliente.adapters.api.views import (
    cerrar_solicitud,
    crear_ticket_java,
    detalle_solicitud,
    eliminar_solicitud,
    estadisticas_solicitudes,
    listar_solicitudes_por_estado,
    listar_solicitudes_por_usuario,
    responder_solicitud,
)

urlpatterns = [
    # ---- Compatibilidad API estilo JavaSpringBoot (/api/atencion-cliente/...) ----
    # Nota: Technova/urls.py monta este archivo tanto en /api/v1/atencion-cliente/ como en /api/atencion-cliente/
    # así que estas rutas quedarán accesibles en ambos prefijos.
    path("estadisticas/", estadisticas_solicitudes, name="atencion_estadisticas_java"),
    path("usuario/<int:usuario_id>/", listar_solicitudes_por_usuario, name="atencion_listar_usuario_java"),
    path("estado/<str:estado>/", listar_solicitudes_por_estado, name="atencion_listar_estado_java"),
    path("<int:solicitud_id>/", detalle_solicitud, name="atencion_detalle_java"),
    path("<int:solicitud_id>/responder/", responder_solicitud, name="atencion_responder_java"),
    path("<int:solicitud_id>/cerrar/", cerrar_solicitud, name="atencion_cerrar_java"),
    path("<int:solicitud_id>/eliminar/", eliminar_solicitud, name="atencion_eliminar_java"),
    path("", crear_ticket_java, name="atencion_crear_java"),

    path("solicitudes/", listar_solicitudes, name="listar_solicitudes"),
    path("solicitudes/crear/", crear_solicitud, name="crear_solicitud"),
    path("solicitudes/estadisticas/", estadisticas_solicitudes, name="solicitudes_estadisticas"),
    path("solicitudes/<int:solicitud_id>/", detalle_solicitud, name="solicitud_detalle"),
    path(
        "solicitudes/<int:solicitud_id>/responder/",
        responder_solicitud,
        name="solicitud_responder",
    ),
    path("solicitudes/<int:solicitud_id>/cerrar/", cerrar_solicitud, name="solicitud_cerrar"),
    path("solicitudes/<int:solicitud_id>/eliminar/", eliminar_solicitud, name="solicitud_eliminar"),
    path("reclamos/", listar_reclamos, name="listar_reclamos"),
    path("reclamos/crear/", crear_reclamo, name="crear_reclamo"),
]
