"""
Al crear un usuario con rol cliente se dispara el correo de bienvenida tras el commit.
"""

from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from usuario.infrastructure.cuenta_correo_email import (
    enviar_bienvenida_correo,
    programar_envio_bienvenida_en_hilo,
)
from usuario.infrastructure.models.usuario_model import Usuario


@receiver(
    post_save,
    sender=Usuario,
    dispatch_uid="technova_usuario_cliente_bienvenida_email",
)
def cliente_nuevo_correo_bienvenida(
    sender,
    instance: Usuario,
    created: bool,
    **kwargs,
) -> None:
    if kwargs.get("raw"):
        return
    if not created:
        return
    if instance.rol != Usuario.Rol.CLIENTE:
        return

    uid = instance.pk

    def _enqueue() -> None:
        if getattr(settings, "TECHNOVA_EMAIL_REGISTRO_ASYNC", False):
            programar_envio_bienvenida_en_hilo(uid)
        else:
            enviar_bienvenida_correo(uid)

    transaction.on_commit(_enqueue)
