from django.urls import path

from pagos.views import (
    actualizar_estado_pago,
    crear_metodo_usuario,
    listar_metodos_usuario,
    listar_pagos,
    registrar_pago,
)

urlpatterns = [
    path("", listar_pagos, name="listar_pagos"),
    path("registrar/", registrar_pago, name="registrar_pago"),
    path("<int:pago_id>/estado/", actualizar_estado_pago, name="actualizar_estado_pago"),
    path("metodos-usuario/", listar_metodos_usuario, name="listar_metodos_usuario"),
    path("metodos-usuario/crear/", crear_metodo_usuario, name="crear_metodo_usuario"),
]
