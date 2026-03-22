from django.urls import path

from compra.views import (
    actualizar_estado_compra,
    detalle_compra,
    listar_compras,
    mis_compras,
    registrar_compra,
)

urlpatterns = [
    path("registrar/", registrar_compra, name="registrar_compra"),
    path("mias/", mis_compras, name="mis_compras"),
    path("<int:compra_id>/estado/", actualizar_estado_compra, name="compra_estado"),
    path("<int:compra_id>/", detalle_compra, name="detalle_compra"),
    path("", listar_compras, name="listar_compras"),
]
