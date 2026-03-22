from django.urls import path

from usuario.adapters.api.usuario_api_views import (
    activar_cuenta,
    catalogo_usuarios,
    patch_estado_usuario,
    recuperar_contrasena,
    usuario_por_id,
    usuarios_login_compat,
    verificar_estado,
    verificar_identidad,
)

urlpatterns = [
    path("verificar-identidad/", verificar_identidad, name="usuarios_verificar_identidad"),
    path("recuperar-contrasena/", recuperar_contrasena, name="usuarios_recuperar_contrasena"),
    path("activar-cuenta/", activar_cuenta, name="usuarios_activar_cuenta"),
    path("login/", usuarios_login_compat, name="usuarios_login_compat"),
    path("verificar-estado/", verificar_estado, name="usuarios_verificar_estado"),
    path("<int:usuario_id>/estado/", patch_estado_usuario, name="usuarios_patch_estado"),
    path("<int:usuario_id>/", usuario_por_id, name="usuarios_por_id"),
    path("", catalogo_usuarios, name="usuarios_catalogo"),
]
