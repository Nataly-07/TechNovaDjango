"""
Señales de dominio para notificar a administradores (inventario).
"""
from __future__ import annotations

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from mensajeria.services.notificaciones_admin import (
    STOCK_BAJO_UMBRAL,
    notificar_producto_agotado,
    notificar_producto_nuevo,
    notificar_stock_bajo,
)
from producto.models import Producto


@receiver(pre_save, sender=Producto)
def producto_pre_save(sender, instance: Producto, **kwargs) -> None:
    if instance.pk:
        try:
            prev = Producto.objects.get(pk=instance.pk)
            instance._stock_previo = prev.stock  # type: ignore[attr-defined]
        except Producto.DoesNotExist:
            instance._stock_previo = None  # type: ignore[attr-defined]
    else:
        instance._stock_previo = None  # type: ignore[attr-defined]


@receiver(post_save, sender=Producto)
def producto_post_save(sender, instance: Producto, created: bool, **kwargs) -> None:
    update_fields = kwargs.get("update_fields")
    if created:
        notificar_producto_nuevo(instance.id, instance.nombre, int(instance.stock))
        return

    if update_fields is not None:
        uf = set(update_fields)
        if uf <= {"stock", "actualizado_en"}:
            return

    prev = getattr(instance, "_stock_previo", None)
    if prev is not None and prev == instance.stock:
        return

    if instance.stock == 0:
        notificar_producto_agotado(instance.id, instance.nombre)
    elif 0 < instance.stock <= STOCK_BAJO_UMBRAL:
        notificar_stock_bajo(instance.id, instance.nombre, int(instance.stock))
