from django.apps import AppConfig


class FarmaciaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'farmacia'
    verbose_name = 'Sistema de Farmacia Penitenciaria'

    def ready(self):
        import farmacia.signals  # noqa
