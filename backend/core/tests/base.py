"""
Base classes for tests in the penitentiary pharmacy system.

This module provides base test classes that handle common setup like:
- Disabling throttling
- Creating authenticated API clients
- Setting up common test data

Usage:
    from core.tests.base import BaseAPITestCase

    class MyTest(BaseAPITestCase):
        def test_something(self):
            # self.client is already authenticated
            response = self.client.get('/api/v1/endpoint/')
"""

from django.test import TestCase, override_settings
from django.contrib.auth.models import Group
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from core.models import User, Centro


# Override throttle settings for all tests
THROTTLE_OVERRIDE = {
    'DEFAULT_THROTTLE_CLASSES': [],
    'DEFAULT_THROTTLE_RATES': {
        'anon': None,
        'user': None,
        'import': None,
        'login': None,
        'password_change': None,
    }
}


class NoThrottleMixin:
    """
    Mixin that disables all throttling for test classes.
    
    Use this mixin with any test class to ensure rate limiting
    doesn't interfere with tests.
    """
    
    @classmethod
    def setUpClass(cls):
        """Apply throttle overrides before tests run."""
        super().setUpClass()
        # Import here to avoid circular imports
        from django.conf import settings
        cls._original_throttle_classes = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_CLASSES', [])
        cls._original_throttle_rates = settings.REST_FRAMEWORK.get('DEFAULT_THROTTLE_RATES', {})
        
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
            'anon': None,
            'user': None,
            'import': None,
            'login': None,
            'password_change': None,
        }
    
    @classmethod
    def tearDownClass(cls):
        """Restore original throttle settings after tests."""
        from django.conf import settings
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = cls._original_throttle_classes
        settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = cls._original_throttle_rates
        super().tearDownClass()


class BaseTestCase(NoThrottleMixin, TestCase):
    """
    Base test case with throttling disabled.
    
    Use for tests that don't need the DRF API client.
    """
    pass


class BaseAPITestCase(NoThrottleMixin, APITestCase):
    """
    Base API test case with throttling disabled and common setup.
    
    Provides:
    - Pre-authenticated admin user and client
    - Common test data creation methods
    - Helper methods for API testing
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = APIClient()
        
        # Create default test user (admin)
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='Admin@123',
            email='admin@test.com',
            is_superuser=True,
            is_staff=True,
            rol='admin_sistema'
        )
        
        # Create standard groups
        self.grupo_farmacia, _ = Group.objects.get_or_create(name='FARMACIA')
        self.grupo_centro, _ = Group.objects.get_or_create(name='CENTRO')
        self.grupo_vista, _ = Group.objects.get_or_create(name='VISTA')
        
    def authenticate_as_admin(self):
        """Authenticate client as admin user."""
        self.client.force_authenticate(user=self.admin_user)
        return self.admin_user
    
    def authenticate_as(self, user):
        """Authenticate client as specific user."""
        self.client.force_authenticate(user=user)
        return user
    
    def get_token(self, username, password):
        """Get JWT token for credentials."""
        response = self.client.post('/api/token/', {
            'username': username,
            'password': password
        })
        if response.status_code == status.HTTP_200_OK:
            return response.data.get('access')
        return None
    
    def authenticate_with_token(self, token):
        """Set Authorization header with Bearer token."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    
    def create_test_user(self, username='testuser', password='Test@123', **kwargs):
        """Create a test user with given parameters."""
        defaults = {
            'email': f'{username}@test.com',
            'rol': 'usuario_normal',
        }
        defaults.update(kwargs)
        return User.objects.create_user(
            username=username,
            password=password,
            **defaults
        )
    
    def create_farmacia_user(self, username='farmacia_user'):
        """Create a user with farmacia role."""
        user = self.create_test_user(
            username=username,
            rol='farmacia'
        )
        user.groups.add(self.grupo_farmacia)
        return user
    
    def create_centro_user(self, username='centro_user', centro=None):
        """Create a user with centro role."""
        user = self.create_test_user(
            username=username,
            rol='centro',
            centro=centro
        )
        user.groups.add(self.grupo_centro)
        return user
    
    def create_test_centro(self, clave='TEST-001', nombre='Centro de Prueba'):
        """Create a test centro."""
        return Centro.objects.create(
            clave=clave,
            nombre=nombre,
            activo=True
        )

    def assertResponseOk(self, response):
        """Assert response is 2xx."""
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_204_NO_CONTENT],
            f"Expected 2xx, got {response.status_code}: {getattr(response, 'data', response.content)}"
        )
    
    def assertResponseForbidden(self, response):
        """Assert response is 403 Forbidden."""
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            f"Expected 403, got {response.status_code}: {getattr(response, 'data', response.content)}"
        )
    
    def assertResponseUnauthorized(self, response):
        """Assert response is 401 Unauthorized."""
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            f"Expected 401, got {response.status_code}: {getattr(response, 'data', response.content)}"
        )
    
    def assertResponseBadRequest(self, response):
        """Assert response is 400 Bad Request."""
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            f"Expected 400, got {response.status_code}: {getattr(response, 'data', response.content)}"
        )
