"""
Difusión en tiempo real del módulo Mensajes (admin ↔ empleado), alineado con MensajeEmpleado en Spring Boot.
"""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def mensajes_group_name(empleado_thread_id: int) -> str:
    return f"mensajes_{int(empleado_thread_id)}"


def broadcast_mensajes_event(empleado_thread_id: int, payload: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        mensajes_group_name(empleado_thread_id),
        {"type": "mensajes_push", "payload": payload},
    )
