from django.urls import path

from envio.views import (
    crear_transportadora,
    envio_por_id,
    listar_envios,
    listar_transportadoras,
    registrar_envio,
)

urlpatterns = [
    path("registrar/", registrar_envio, name="registrar_envio"),
    path("transportadoras/crear/", crear_transportadora, name="crear_transportadora"),
    path("transportadoras/", listar_transportadoras, name="listar_transportadoras"),
    path("<int:envio_id>/", envio_por_id, name="envio_por_id"),
    path("", listar_envios, name="listar_envios"),
]
