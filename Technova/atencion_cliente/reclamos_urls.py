from django.urls import path

from atencion_cliente.adapters.api.reclamos_views import (
    cerrar_reclamo,
    crear_reclamo,
    detalle_o_eliminar_reclamo,
    enviar_reclamo_admin,
    evaluar_resolucion,
    listar_reclamos_estado,
    listar_reclamos_usuario,
    responder_reclamo,
)

urlpatterns = [
    path(
        "<int:reclamo_id>/evaluar-resolucion/",
        evaluar_resolucion,
        name="reclamo_evaluar_resolucion",
    ),
    path(
        "<int:reclamo_id>/enviar-al-admin/",
        enviar_reclamo_admin,
        name="reclamo_enviar_admin",
    ),
    path("<int:reclamo_id>/responder/", responder_reclamo, name="reclamo_responder"),
    path("<int:reclamo_id>/cerrar/", cerrar_reclamo, name="reclamo_cerrar"),
    path("usuario/<int:usuario_id>/", listar_reclamos_usuario, name="reclamos_por_usuario"),
    path("estado/<str:estado>/", listar_reclamos_estado, name="reclamos_por_estado"),
    path("<int:reclamo_id>/", detalle_o_eliminar_reclamo, name="reclamo_detalle_o_eliminar"),
    path("", crear_reclamo, name="reclamo_crear"),
]
