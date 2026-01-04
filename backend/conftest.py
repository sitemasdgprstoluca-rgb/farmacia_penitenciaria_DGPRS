"""
Pytest configuration for the backend tests.
"""
import pytest
from django.conf import settings


def pytest_configure():
    """Configure Django settings for pytest."""
    settings.DEBUG = False
    settings.TESTING = True


# ISS-TEST FIX: Forzar managed=True para tests con SQLite
# Los modelos tienen managed=False porque la BD es Supabase, pero
# para tests locales necesitamos que Django cree las tablas en SQLite.
@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """
    Configura la base de datos de tests.
    
    Fuerza managed=True temporalmente para que Django cree las tablas
    de modelos que tienen managed=False (para compatibilidad con Supabase).
    """
    from django.apps import apps
    from django.db import connection
    
    # Obtener todos los modelos con managed=False
    unmanaged_models = []
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if hasattr(model._meta, 'managed') and not model._meta.managed:
                unmanaged_models.append(model)
                model._meta.managed = True
    
    with django_db_blocker.unblock():
        # Crear las tablas
        from django.core.management import call_command
        call_command('migrate', '--run-syncdb', verbosity=0)
        
        # Crear tablas para modelos unmanaged
        with connection.schema_editor() as schema_editor:
            for model in unmanaged_models:
                try:
                    schema_editor.create_model(model)
                except Exception:
                    # La tabla puede ya existir
                    pass
    
    yield
    
    # Restaurar managed=False (opcional, limpieza)
    for model in unmanaged_models:
        model._meta.managed = False


@pytest.fixture
def api_client():
    """Create a DRF API client for testing."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, django_user_model, db):
    """Create an authenticated API client."""
    user = django_user_model.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='testpass123',
        rol='ADMIN'
    )
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_user(django_user_model, db):
    """Create an admin user for testing."""
    return django_user_model.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='adminpass123',
        rol='ADMIN'
    )
