from django.urls import path

from producto.adapters.api.caracteristicas_views import (
    caracteristica_por_id,
    caracteristicas_raiz,
)

urlpatterns = [
    path("<int:caracteristica_id>/", caracteristica_por_id, name="caracteristica_por_id"),
    path("", caracteristicas_raiz, name="caracteristicas_raiz"),
]
