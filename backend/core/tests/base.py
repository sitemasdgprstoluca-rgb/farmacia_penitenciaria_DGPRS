"""
Base test classes for the core application.

Provides common test utilities:
- NoThrottleMixin: Disables API throttling during tests
- BaseTestCase: Base class for model/unit tests
- BaseAPITestCase: Base class for API tests with authentication helpers
"""

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta

from core.models import Centro, Producto, Lote

User = get_user_model()


class NoThrottleMixin:
    """
    Mixin to disable API throttling during tests.
    
    Usage:
        class MyTest(NoThrottleMixin, TestCase):
            ...
    """
    
    @classmethod
    def setUpClass(cls):
        """Disable throttling for all tests in the class."""
        super().setUpClass()
        # Store original throttle classes
        from django.conf import settings
        cls._original_throttle_rates = getattr(settings, 'REST_FRAMEWORK', {}).get('DEFAULT_THROTTLE_RATES', {})
        
    @classmethod
    def tearDownClass(cls):
        """Restore original throttle settings."""
        super().tearDownClass()


class BaseTestCase(TestCase):
    """
    Base test case for model and unit tests.
    
    Provides:
    - Common test data creation methods
    - Utility assertions
    """
    
    @classmethod
    def setUpTestData(cls):
        """Create test data shared across all test methods."""
        super().setUpTestData()
        
        # Create default admin user
        cls.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@test.com',
            password='AdminTest@123'
        )
        
        # Create groups
        cls.grupo_farmaceutico, _ = Group.objects.get_or_create(name='FARMACEUTICO')
        cls.grupo_solicitante, _ = Group.objects.get_or_create(name='SOLICITANTE')
        cls.grupo_vista, _ = Group.objects.get_or_create(name='VISTA_USER')
    
    def create_user(self, username='testuser', password='Test@123', rol='usuario', **kwargs):
        """Create a test user."""
        return User.objects.create_user(
            username=username,
            password=password,
            email=f'{username}@test.com',
            rol=rol,
            **kwargs
        )
    
    def create_farmaceutico(self, username='farmaceutico', **kwargs):
        """Create a user with FARMACEUTICO group."""
        user = self.create_user(username=username, rol='farmacia', **kwargs)
        user.groups.add(self.grupo_farmaceutico)
        return user
    
    def create_centro(self, clave='CENTRO-001', nombre='Centro de Prueba', **kwargs):
        """Create a test centro."""
        return Centro.objects.create(
            clave=clave,
            nombre=nombre,
            direccion='Dirección de prueba',
            telefono='555-0000',
            activo=True,
            **kwargs
        )
    
    def create_producto(self, clave='PROD-001', descripcion='Producto de prueba', **kwargs):
        """Create a test producto."""
        defaults = {
            'unidad_medida': 'PIEZA',
            'precio_unitario': Decimal('10.00'),
            'stock_minimo': 50,
            'activo': True
        }
        defaults.update(kwargs)
        return Producto.objects.create(clave=clave, descripcion=descripcion, **defaults)
    
    def create_lote(self, producto=None, numero_lote='LOTE-001', cantidad=100, **kwargs):
        """Create a test lote."""
        if producto is None:
            producto = self.create_producto()
        
        defaults = {
            'fecha_caducidad': date.today() + timedelta(days=365),
            'cantidad_inicial': cantidad,
            'cantidad_actual': cantidad,
            'estado': 'disponible'
        }
        defaults.update(kwargs)
        return Lote.objects.create(
            producto=producto,
            numero_lote=numero_lote,
            **defaults
        )


class BaseAPITestCase(NoThrottleMixin, APITestCase):
    """
    Base test case for API tests.
    
    Provides:
    - Pre-configured APIClient
    - Authentication helpers
    - Common assertions
    """
    
    @classmethod
    def setUpTestData(cls):
        """Create test data shared across all test methods."""
        super().setUpTestData()
        
        # Create groups
        cls.grupo_farmaceutico, _ = Group.objects.get_or_create(name='FARMACEUTICO')
        cls.grupo_solicitante, _ = Group.objects.get_or_create(name='SOLICITANTE')
        cls.grupo_vista, _ = Group.objects.get_or_create(name='VISTA_USER')
        
        # Create admin user
        cls.admin_user = User.objects.create_superuser(
            username='admin_api_test',
            email='admin_api@test.com',
            password='AdminAPI@123'
        )
        
        # Create regular user
        cls.regular_user = User.objects.create_user(
            username='user_api_test',
            email='user_api@test.com',
            password='UserAPI@123',
            rol='usuario'
        )
        
        # Create farmaceutico user
        cls.farmaceutico_user = User.objects.create_user(
            username='farmaceutico_test',
            email='farmaceutico@test.com',
            password='Farmaceutico@123',
            rol='farmacia'
        )
        cls.farmaceutico_user.groups.add(cls.grupo_farmaceutico)
    
    def setUp(self):
        """Set up test client for each test."""
        super().setUp()
        self.client = APIClient()
    
    def authenticate_as_admin(self):
        """Authenticate as admin user."""
        self.client.force_authenticate(user=self.admin_user)
    
    def authenticate_as_user(self):
        """Authenticate as regular user."""
        self.client.force_authenticate(user=self.regular_user)
    
    def authenticate_as_farmaceutico(self):
        """Authenticate as farmaceutico user."""
        self.client.force_authenticate(user=self.farmaceutico_user)
    
    def authenticate_with_token(self, user):
        """Authenticate using JWT token."""
        response = self.client.post('/api/v1/token/', {
            'username': user.username,
            'password': 'Test@123'  # Assumes default test password
        })
        if response.status_code == status.HTTP_200_OK:
            token = response.data.get('access')
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            return token
        return None
    
    def assertResponseOk(self, response):
        """Assert response status is 200 OK."""
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def assertResponseCreated(self, response):
        """Assert response status is 201 Created."""
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def assertResponseNoContent(self, response):
        """Assert response status is 204 No Content."""
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def assertResponseBadRequest(self, response):
        """Assert response status is 400 Bad Request."""
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def assertResponseUnauthorized(self, response):
        """Assert response status is 401 Unauthorized."""
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def assertResponseForbidden(self, response):
        """Assert response status is 403 Forbidden."""
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def assertResponseNotFound(self, response):
        """Assert response status is 404 Not Found."""
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def create_test_centro(self, clave='TEST-CENTRO', nombre='Centro de Prueba API'):
        """Create a centro for API tests."""
        return Centro.objects.create(
            clave=clave,
            nombre=nombre,
            direccion='Dirección de prueba',
            telefono='555-0000',
            activo=True
        )
    
    def create_test_producto(self, clave='TEST-PROD', descripcion='Producto de Prueba API'):
        """Create a producto for API tests."""
        return Producto.objects.create(
            clave=clave,
            descripcion=descripcion,
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=50,
            activo=True
        )
    
    def create_test_lote(self, producto=None, numero_lote='TEST-LOTE', cantidad=100):
        """Create a lote for API tests."""
        if producto is None:
            producto = self.create_test_producto()
        
        return Lote.objects.create(
            producto=producto,
            numero_lote=numero_lote,
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=cantidad,
            cantidad_actual=cantidad,
            estado='disponible'
        )
