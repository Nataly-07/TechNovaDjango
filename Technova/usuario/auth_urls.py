from django.urls import path

from usuario.adapters.api.auth_views import login, me, refresh_token

urlpatterns = [
    path("login/", login, name="auth_login"),
    path("refresh/", refresh_token, name="auth_refresh"),
    path("me/", me, name="auth_me"),
]
