from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from usuario.models import Usuario


class UsuarioJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        usuario_id = validated_token.get("usuario_id")
        if not usuario_id:
            raise InvalidToken("El token no contiene usuario_id.")

        try:
            usuario = Usuario.objects.get(id=usuario_id, activo=True)
        except Usuario.DoesNotExist as exc:
            raise InvalidToken("Usuario no encontrado o inactivo.") from exc

        return usuario
