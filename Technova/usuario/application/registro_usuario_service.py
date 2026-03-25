"""
Registro de usuarios (caso de uso de aplicacion).

Compartido por la API JSON y el adaptador web de sesion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.contrib.auth.hashers import make_password
from django.db import IntegrityError

from usuario.models import Usuario


def validar_contrasena_politica(password: str) -> str | None:
    """Devuelve mensaje de error o None si la contrasena cumple la politica."""
    if len(password) < 8:
        return (
            "La contrasena debe tener minimo 8 caracteres, mayuscula, minuscula, "
            "numero y caracter especial"
        )
    if not re.search(r"[A-Z]", password):
        return (
            "La contrasena debe tener minimo 8 caracteres, mayuscula, minuscula, "
            "numero y caracter especial"
        )
    if not re.search(r"[a-z]", password):
        return (
            "La contrasena debe tener minimo 8 caracteres, mayuscula, minuscula, "
            "numero y caracter especial"
        )
    if not re.search(r"\d", password):
        return (
            "La contrasena debe tener minimo 8 caracteres, mayuscula, minuscula, "
            "numero y caracter especial"
        )
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return (
            "La contrasena debe tener minimo 8 caracteres, mayuscula, minuscula, "
            "numero y caracter especial"
        )
    return None


def mensaje_integridad_registro() -> str:
    return (
        "Los datos ingresados ya existen en el sistema. Por favor, verifica tu informacion "
        "(correo o documento duplicado)."
    )


def _payload_str(payload: dict, *keys: str, default: str | None = None) -> str | None:
    for k in keys:
        if k in payload and payload[k] is not None and str(payload[k]).strip() != "":
            return str(payload[k]).strip()
    return default


def _rol_valido(val: str) -> bool:
    return val in {c[0] for c in Usuario.Rol.choices}


@dataclass(frozen=True)
class ResultadoRegistroUsuario:
    usuario: Usuario | None
    error: str | None


def registrar_usuario_desde_payload(
    payload: dict,
    *,
    admin_usuario: Usuario | None = None,
) -> ResultadoRegistroUsuario:
    """
    Crea un usuario cliente (o rol fijado por admin si admin_usuario es admin).

    `payload` usa las mismas claves que la API: email/correo, password, firstName/nombres, etc.
    """
    email = (_payload_str(payload, "email", "correo_electronico", "correo") or "").lower()
    password = _payload_str(payload, "password", "contrasena")
    first_name = _payload_str(payload, "firstName", "nombres")
    last_name = _payload_str(payload, "lastName", "apellidos")
    doc_type = _payload_str(payload, "documentType", "tipo_documento")
    doc_num = _payload_str(payload, "documentNumber", "numero_documento")
    phone = _payload_str(payload, "phone", "telefono")
    address = _payload_str(payload, "address", "direccion") or ""

    if not all([email, password, first_name, last_name, doc_type, doc_num, phone]):
        return ResultadoRegistroUsuario(
            None,
            "Faltan campos requeridos (email, password, nombres, apellidos, documento, telefono).",
        )

    if not doc_num.isdigit():
        return ResultadoRegistroUsuario(
            None,
            "El numero de documento solo debe contener numeros (sin letras ni simbolos).",
        )
    if len(doc_num) < 7 or len(doc_num) > 10:
        return ResultadoRegistroUsuario(
            None,
            "El numero de documento debe tener entre 7 y 10 digitos.",
        )

    err = validar_contrasena_politica(password)
    if err:
        return ResultadoRegistroUsuario(None, err)

    nombre_base = _payload_str(payload, "name", "nombre_usuario") or email.split("@")[0]
    nombre_usuario = nombre_base
    suffix = 0
    while Usuario.objects.filter(nombre_usuario=nombre_usuario).exists():
        suffix += 1
        nombre_usuario = f"{nombre_base}{suffix}"

    rol = Usuario.Rol.CLIENTE
    raw_rol = (_payload_str(payload, "role", "rol") or "").lower()
    if admin_usuario and admin_usuario.rol == Usuario.Rol.ADMIN and raw_rol and _rol_valido(raw_rol):
        rol = raw_rol

    try:
        usuario = Usuario.objects.create(
            nombre_usuario=nombre_usuario,
            correo_electronico=email,
            contrasena_hash=make_password(password),
            nombres=first_name,
            apellidos=last_name,
            tipo_documento=doc_type,
            numero_documento=doc_num,
            telefono=phone,
            direccion=address,
            rol=rol,
            activo=True,
        )
    except IntegrityError:
        return ResultadoRegistroUsuario(None, mensaje_integridad_registro())

    from mensajeria.services.notificaciones_admin import notificar_usuario_nuevo

    notificar_usuario_nuevo(usuario)

    return ResultadoRegistroUsuario(usuario, None)
