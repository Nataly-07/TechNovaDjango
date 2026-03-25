from django.apps import AppConfig


class MensajeriaConfig(AppConfig):
    name = "mensajeria"

    def ready(self) -> None:
        import mensajeria.signals  # noqa: F401
