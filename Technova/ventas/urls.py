from django.urls import path

from ventas.views import anular_venta, checkout, listar_ventas

urlpatterns = [
    path("", listar_ventas, name="listar_ventas"),
    path("checkout/", checkout, name="checkout_venta"),
    path("<int:venta_id>/anular/", anular_venta, name="anular_venta"),
]
