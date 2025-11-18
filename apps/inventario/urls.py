# filepath: apps/inventario/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Vista simple para probar que el módulo funciona
    path("", views.home, name="inventario_home"),
]
