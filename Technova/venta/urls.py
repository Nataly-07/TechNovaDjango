from django.urls import path

from venta.views import anular_venta, checkout, detalle_venta, listar_ventas, mis_ventas

urlpatterns = [
    path("checkout/", checkout, name="checkout_venta"),
    path("mias/", mis_ventas, name="mis_ventas"),
    path("<int:venta_id>/anular/", anular_venta, name="anular_venta"),
    path("<int:venta_id>/", detalle_venta, name="detalle_venta"),
    path("", listar_ventas, name="listar_ventas"),
]
