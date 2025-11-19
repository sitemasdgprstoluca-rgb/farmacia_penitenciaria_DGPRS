from django.apps import AppConfig


class InventarioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.inventario'
    label = 'inventario'
    verbose_name = 'Sistema de Inventario'
