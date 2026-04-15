from django.apps import AppConfig


class UsuarioConfig(AppConfig):
    name = "usuario"

    def ready(self) -> None:
        import usuario.checks  # noqa: F401
        import usuario.signals  # noqa: F401

        from django.conf import settings

        if settings.DEBUG:
            print(
                "[Technova dev] settings.EMAIL_HOST_USER =",
                repr(getattr(settings, "EMAIL_HOST_USER", None)),
                flush=True,
            )
