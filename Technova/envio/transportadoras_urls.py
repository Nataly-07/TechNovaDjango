from django.urls import path

from envio.adapters.api.transportadoras_views import (
    transportadora_por_id,
    transportadoras_por_envio,
    transportadoras_raiz,
)

urlpatterns = [
    path("envio/<int:envio_id>/", transportadoras_por_envio, name="transportadoras_por_envio"),
    path("<int:transportadora_id>/", transportadora_por_id, name="transportadora"),
    path("", transportadoras_raiz, name="transportadoras_raiz"),
]
