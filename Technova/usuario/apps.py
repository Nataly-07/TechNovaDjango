from django.apps import AppConfig


class UsuarioConfig(AppConfig):
    name = "usuario"

    def ready(self) -> None:
        import usuario.checks  # noqa: F401
        import usuario.signals  # noqa: F401
