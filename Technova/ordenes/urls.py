from django.urls import path

from ordenes.views import listar_ordenes, registrar_orden

urlpatterns = [
    path("", listar_ordenes, name="listar_ordenes"),
    path("registrar/", registrar_orden, name="registrar_orden"),
]
