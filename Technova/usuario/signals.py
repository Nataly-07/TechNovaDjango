"""
Al crear un usuario con rol cliente se genera token de verificación y se programa
el envío del correo (en hilo) tras el commit de la transacción.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from usuario.infrastructure.cuenta_correo_email import (
    enviar_bienvenida_y_confirmacion_correo,
    programar_envio_bienvenida_en_hilo,
)
from usuario.infrastructure.models.usuario_model import Usuario


@receiver(post_save, sender=Usuario)
def cliente_nuevo_token_y_correo_bienvenida(
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
    if instance.correo_verificado:
        return

    token = secrets.token_urlsafe(48)
    expira = timezone.now() + timedelta(days=7)
    Usuario.objects.filter(pk=instance.pk).update(
        token_verificacion_correo=token,
        token_verificacion_expira=expira,
    )

    uid = instance.pk

    def _enqueue() -> None:
        if getattr(settings, "TECHNOVA_EMAIL_REGISTRO_ASYNC", False):
            programar_envio_bienvenida_en_hilo(uid)
        else:
            enviar_bienvenida_y_confirmacion_correo(uid)

    transaction.on_commit(_enqueue)
