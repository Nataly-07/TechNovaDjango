"""Resolución de cliente para ventas en punto de venta (registrado vs mostrador)."""

from __future__ import annotations

import secrets

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction

from usuario.infrastructure.models.usuario_model import Usuario

# Usuario interno único para cumplir FK en ventas/mediospago sin crear cuentas por comprador.
_SENTINEL_USERNAME = "__technova_pos_mostrador__"


def obtener_usuario_sentinel_mostrador() -> Usuario:
    u = Usuario.objects.filter(nombre_usuario=_SENTINEL_USERNAME).first()
    if u:
        return u
    pwd = secrets.token_urlsafe(32)
    try:
        with transaction.atomic():
            return Usuario.objects.create(
                nombre_usuario=_SENTINEL_USERNAME,
                correo_electronico="pos-mostrador-interno@technova.local",
                contrasena_hash=make_password(pwd),
                nombres="Comprador",
                apellidos="mostrador (sistema interno)",
                tipo_documento="—",
                numero_documento="90000000001",
                telefono="0000000000",
                direccion="No aplica — ventas en mostrador sin cuenta de cliente.",
                rol=Usuario.Rol.CLIENTE,
                activo=False,
            )
    except IntegrityError:
        return Usuario.objects.get(nombre_usuario=_SENTINEL_USERNAME)


def resolver_cliente_para_pos(request) -> tuple[int | None, dict | None, str | None]:
    """
    Devuelve (cliente_id, datos_facturacion_mostrador, mensaje_error).

    - registrado: (id del cliente, None, None).
    - mostrador con documento de cliente ya registrado: (id, None, None) — sin crear usuario.
    - mostrador sin cuenta en el sistema: (id_sentinela, dict con datos de factura, None).
    """
    tipo = (request.POST.get("cliente_tipo") or "registrado").strip().lower()
    if tipo not in ("registrado", "mostrador"):
        return None, None, "Tipo de cliente no válido."

    if tipo == "registrado":
        try:
            cid = int((request.POST.get("cliente_id") or "0") or 0)
        except (TypeError, ValueError):
            return None, None, "Selecciona un cliente registrado."
        if cid <= 0:
            return None, None, "Selecciona un cliente registrado."
        if not Usuario.objects.filter(pk=cid, rol=Usuario.Rol.CLIENTE, activo=True).exists():
            return None, None, "Cliente no válido."
        return cid, None, None

    nombres = (request.POST.get("pv_nombres") or "").strip()
    apellidos = (request.POST.get("pv_apellidos") or "").strip()
    email = (request.POST.get("pv_email") or "").strip().lower()
    telefono = (request.POST.get("pv_telefono") or "").strip()
    tipo_doc = (request.POST.get("pv_tipo_documento") or "").strip()
    num_doc = (request.POST.get("pv_numero_documento") or "").strip()
    direccion = (request.POST.get("pv_direccion") or "").strip()

    if len(nombres) < 2 or len(apellidos) < 2:
        return None, None, "Ingresa nombres y apellidos del comprador (mínimo 2 caracteres cada uno)."
    if not tipo_doc:
        return None, None, "Selecciona el tipo de documento."
    if not num_doc.isdigit() or len(num_doc) < 7 or len(num_doc) > 10:
        return None, None, "El número de documento debe tener entre 7 y 10 dígitos numéricos."
    if len(telefono) < 7 or len(telefono) > 20:
        return None, None, "Ingresa un teléfono válido (7 a 20 caracteres)."

    existente = Usuario.objects.filter(numero_documento=num_doc).first()
    if existente:
        if existente.nombre_usuario == _SENTINEL_USERNAME:
            return None, None, "Documento reservado para el sistema; usa otro número."
        if existente.rol != Usuario.Rol.CLIENTE:
            return None, None, "Ese documento pertenece a un usuario que no es cliente."
        return existente.id, None, None

    correo_guardar = email[:120] if email else ""

    datos = {
        "nombres": nombres[:120],
        "apellidos": apellidos[:120],
        "correo_electronico": correo_guardar,
        "telefono": telefono[:20],
        "tipo_documento": tipo_doc[:30],
        "numero_documento": num_doc[:40],
        "direccion": (direccion or "Compra en punto de venta físico.")[:2000],
    }

    sentinel = obtener_usuario_sentinel_mostrador()
    return sentinel.id, datos, None
