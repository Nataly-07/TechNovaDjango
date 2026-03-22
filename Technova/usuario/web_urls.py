"""Rutas HTML (sesion) del modulo usuario — reservado si se incluye aparte de web.urls."""

from django.urls import path

from usuario.adapters.web.session_views import (
    home_portal,
    login_web,
    logout_web,
    registro_stub,
)
from web.views import home as inicio_autenticado_view, root_entry

urlpatterns = [
    path("", root_entry, name="root"),
    path("inicio/", inicio_autenticado_view, name="inicio_autenticado"),
    path("login/", login_web, name="web_login"),
    path("logout/", logout_web, name="web_logout"),
    path("registro/", registro_stub, name="web_registro"),
    path("cuenta/", home_portal, name="home_portal"),
]
