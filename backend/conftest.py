"""Configuración de pytest para Django."""
import os
import pytest
import django
from django.conf import settings

# Configurar Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')


def pytest_configure(config):
    """Configurar pytest para Django."""
    from django.conf import settings
    
    # Configuración de seguridad para tests
    settings.DEBUG = True
    settings.SECRET_KEY = 'test-secret-key-for-testing-only'
    settings.ALLOWED_HOSTS = ['*']
    settings.PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    
    # ✅ DESACTIVAR THROTTLING EN TESTS
    # Esto previene errores HTTP 429 (Too Many Requests) durante las pruebas
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        'anon': None,
        'user': None,
        'import': None,
        'login': None,
        'password_change': None,
    }
    
    django.setup()


@pytest.fixture(autouse=True)
def disable_throttling():
    """
    Fixture que se ejecuta automáticamente para desactivar throttling.
    Se aplica a todos los tests de pytest.
    """
    from django.conf import settings
    
    # Guardar configuración original
    original_classes = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', [])
    original_rates = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
    
    # Desactivar throttling
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
        'anon': None,
        'user': None,
        'import': None,
        'login': None,
        'password_change': None,
    }
    
    yield
    
    # Restaurar configuración original
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = original_classes
    settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = original_rates


@pytest.fixture
def api_client():
    """Cliente de API para tests."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def create_user(db):
    """Factory para crear usuarios de prueba."""
    from core.models import User, Centro
    
    def _create_user(username, rol='vista', centro=None, **kwargs):
        defaults = {
            'email': f'{username}@test.com',
            'rol': rol,
            'is_active': True,
        }
        defaults.update(kwargs)
        user = User.objects.create_user(username=username, password='Test1234!', **defaults)
        if centro:
            user.centro = centro
            user.save()
        return user
    
    return _create_user


@pytest.fixture
def admin_user(create_user):
    """Usuario admin para tests."""
    return create_user('admin_test', rol='admin_sistema', is_superuser=True, is_staff=True)


@pytest.fixture
def farmacia_user(create_user):
    """Usuario farmacia para tests."""
    return create_user('farmacia_test', rol='farmacia')


@pytest.fixture
def centro_user(db, create_user):
    """Usuario de centro para tests."""
    from core.models import Centro
    centro = Centro.objects.create(nombre='Centro Test', clave='CT01')
    return create_user('centro_test', rol='centro', centro=centro)


@pytest.fixture
def vista_user(create_user):
    """Usuario vista para tests."""
    return create_user('vista_test', rol='vista')


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """Cliente autenticado como admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client
