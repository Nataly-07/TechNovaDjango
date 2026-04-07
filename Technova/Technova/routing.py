from django.urls import path

from mensajeria.consumers import MensajesConsumer

websocket_urlpatterns = [
    path("ws/mensajes/<int:empleado_id>/", MensajesConsumer.as_asgi()),
]
