from django.urls import path

from pago.adapters.api.medios_pago_views import (
    medio_pago_por_id,
    medios_pago_raiz,
)

urlpatterns = [
    path("<int:medio_id>/", medio_pago_por_id, name="medio_pago"),
    path("", medios_pago_raiz, name="medios_pago_raiz"),
]
