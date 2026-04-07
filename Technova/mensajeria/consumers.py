"""
Consumidor WebSocket — módulo Mensajes (admin ↔ empleado), autenticación por sesión web.
"""

from __future__ import annotations

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from mensajeria.infrastructure.realtime_mensajes import mensajes_group_name
from usuario.adapters.web.session_views import SESSION_USUARIO_ID
from usuario.models import Usuario


@database_sync_to_async
def _usuario_desde_sesion(session) -> Usuario | None:
    uid = session.get(SESSION_USUARIO_ID)
    if not uid:
        return None
    return Usuario.objects.filter(pk=uid).first()


@database_sync_to_async
def _puede_acceder_hilo(empleado_thread_id: int, usuario: Usuario) -> bool:
    if usuario.rol == Usuario.Rol.ADMIN:
        return Usuario.objects.filter(pk=empleado_thread_id, rol=Usuario.Rol.EMPLEADO).exists()
    if usuario.rol == Usuario.Rol.EMPLEADO:
        return empleado_thread_id == usuario.id
    return False


class MensajesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.emp_thread_id = int(self.scope["url_route"]["kwargs"]["empleado_id"])
        session = self.scope.get("session")
        if session is None:
            await self.close()
            return
        usuario = await _usuario_desde_sesion(session)
        if usuario is None:
            await self.close()
            return
        if not await _puede_acceder_hilo(self.emp_thread_id, usuario):
            await self.close()
            return
        self.group_name = mensajes_group_name(self.emp_thread_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        gn = getattr(self, "group_name", None)
        if gn:
            await self.channel_layer.group_discard(gn, self.channel_name)

    async def mensajes_push(self, event):
        await self.send(text_data=json.dumps(event["payload"], ensure_ascii=False))
