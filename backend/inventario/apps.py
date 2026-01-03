import os
from django.apps import AppConfig


class InventarioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventario'
    label = 'inventario'
    verbose_name = 'Sistema de Inventario'
    path = os.path.dirname(os.path.abspath(__file__))
