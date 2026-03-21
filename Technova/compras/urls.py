from django.urls import path

from compras.views import registrar_compra

urlpatterns = [
    path("registrar/", registrar_compra, name="registrar_compra"),
]
