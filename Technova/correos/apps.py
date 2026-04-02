from django.apps import AppConfig


class CorreosConfig(AppConfig):
    name = 'correos'
    
    def ready(self):
        import correos.signals
