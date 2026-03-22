"""
Autenticacion por correo y contrasena (caso de uso de aplicacion).

Los adaptadores HTTP (API JSON, sesion web) delegan aqui la logica compartida.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.hashers import check_password, make_password

from usuario.models import Usuario


def credenciales_coinciden(password_plano: str, valor_guardado: str) -> bool:
    """Comprueba contrasena plana contra hash Django o valor legacy en texto plano."""
    if not valor_guardado:
        return False
    if valor_guardado.startswith(("pbkdf2_", "argon2$", "bcrypt$", "scrypt$")):
        return check_password(password_plano, valor_guardado)
    return password_plano == valor_guardado


@dataclass(frozen=True)
class ResultadoAutenticacion:
    usuario: Usuario | None
    """Si error es None, usuario esta definido."""

    error: str | None
    """'credenciales' | 'inactivo' | None si ok."""


def autenticar_por_correo(
    correo: str,
    password: str,
    *,
    tratar_inactivo_como_credenciales_invalidas: bool = True,
) -> ResultadoAutenticacion:
    """
    Valida correo/contrasena y migra hash legacy a Django en el primer login exitoso.

    Si tratar_inactivo_como_credenciales_invalidas es True, cuenta inactiva se reporta
    como error 'credenciales' (mismo mensaje que usuario inexistente o clave mala).
    """
    correo_norm = (correo or "").strip().lower()
    try:
        usuario = Usuario.objects.get(correo_electronico__iexact=correo_norm)
    except Usuario.DoesNotExist:
        return ResultadoAutenticacion(None, "credenciales")

    if not usuario.activo:
        if tratar_inactivo_como_credenciales_invalidas:
            return ResultadoAutenticacion(None, "credenciales")
        return ResultadoAutenticacion(None, "inactivo")

    if not credenciales_coinciden(password, usuario.contrasena_hash):
        return ResultadoAutenticacion(None, "credenciales")

    if not usuario.contrasena_hash.startswith(("pbkdf2_", "argon2$", "bcrypt$", "scrypt$")):
        usuario.contrasena_hash = make_password(password)
        usuario.save(update_fields=["contrasena_hash", "actualizado_en"])

    return ResultadoAutenticacion(usuario, None)
