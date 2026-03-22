from django.urls import path

from orden.views import actualizar_estado_orden, detalle_orden, listar_ordenes, registrar_orden

urlpatterns = [
    path("registrar/", registrar_orden, name="registrar_orden"),
    path("<int:orden_id>/estado/", actualizar_estado_orden, name="orden_estado"),
    path("<int:orden_id>/", detalle_orden, name="detalle_orden"),
    path("", listar_ordenes, name="listar_ordenes"),
]
