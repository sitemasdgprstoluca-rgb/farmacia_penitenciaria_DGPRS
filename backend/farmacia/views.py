"""
Archivo legacy sin uso. Las rutas oficiales viven en backend/config/api_urls.py.
Se deja como stub para evitar importaciones accidentales de viewsets duplicados.
"""
from django.core.exceptions import ImproperlyConfigured


def __getattr__(name):
  raise ImproperlyConfigured("Las vistas de 'farmacia' están obsoletas. Usa backend/config/api_urls.py")
