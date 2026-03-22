"""Rutas HTML (sesion) del modulo usuario."""

from django.urls import path

from usuario.adapters.web.session_views import (
    home_portal,
    index_public,
    login_web,
    logout_web,
    registro_stub,
)

urlpatterns = [
    path("", index_public, name="index_public"),
    path("login/", login_web, name="web_login"),
    path("logout/", logout_web, name="web_logout"),
    path("registro/", registro_stub, name="web_registro"),
    path("cuenta/", home_portal, name="home_portal"),
]
