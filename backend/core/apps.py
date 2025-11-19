from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    label = 'core'
    verbose_name = 'Core del Sistema'

    def ready(self):
        # Importar signals al iniciar la app
        from . import signals  # noqa: F401
