from django.urls import path

from envios.views import (
    crear_transportadora,
    listar_envios,
    listar_transportadoras,
    registrar_envio,
)

urlpatterns = [
    path("", listar_envios, name="listar_envios"),
    path("registrar/", registrar_envio, name="registrar_envio"),
    path("transportadoras/", listar_transportadoras, name="listar_transportadoras"),
    path("transportadoras/crear/", crear_transportadora, name="crear_transportadora"),
]
