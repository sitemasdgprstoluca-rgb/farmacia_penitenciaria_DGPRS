"""
Tests de autenticación JWT y permisos.

Este módulo utiliza BaseAPITestCase que desactiva automáticamente
el rate limiting para evitar errores HTTP 429 durante las pruebas.
"""

from django.test import TestCase
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status
from core.models import User, Centro
from core.tests.base import BaseAPITestCase, NoThrottleMixin


class AuthenticationTest(NoThrottleMixin, TestCase):
    """Tests de autenticación JWT"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Crear usuario de prueba
        self.user = User.objects.create_user(
            username='testuser',
            password='Test@123',
            email='test@test.com'
        )
    
    def test_obtener_token(self):
        """Obtener token JWT con credenciales válidas"""
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'Test@123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
    
    def test_token_credenciales_invalidas(self):
        """Token no se genera con credenciales inválidas"""
        response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'WrongPassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_acceso_protegido_sin_token(self):
        """Endpoints protegidos requieren autenticación"""
        response = self.client.get('/api/v1/productos/')
        # Acepta 401 o 403 (ambos correctos para endpoints protegidos)
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_acceso_protegido_con_token(self):
        """Acceso a endpoints con token válido"""
        # Obtener token
        login_response = self.client.post('/api/token/', {
            'username': 'testuser',
            'password': 'Test@123'
        })
        
        token = login_response.data['access']
        
        # Usar token en request
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/productos/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PermissionTest(NoThrottleMixin, TestCase):
    """Tests de permisos por grupo"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Crear grupos
        self.grupo_farmaceutico = Group.objects.create(name='FARMACEUTICO')
        self.grupo_solicitante = Group.objects.create(name='SOLICITANTE')
        
        # Crear usuarios
        self.farmaceutico = User.objects.create_user(
            username='farmaceutico',
            password='Test@123'
        )
        self.farmaceutico.groups.add(self.grupo_farmaceutico)
        
        self.solicitante = User.objects.create_user(
            username='solicitante',
            password='Test@123'
        )
        self.solicitante.groups.add(self.grupo_solicitante)
    
    def test_farmaceutico_puede_crear_producto(self):
        """FARMACEUTICO puede crear productos"""
        # Login como farmaceutico
        response = self.client.post('/api/token/', {
            'username': 'farmaceutico',
            'password': 'Test@123'
        })
        
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Intentar crear producto
        response = self.client.post('/api/v1/productos/', {
            'clave': 'TEST-001',
            'descripcion': 'Producto de prueba',
            'unidad_medida': 'PIEZA',
            'precio_unitario': '10.00',
            'stock_minimo': 50
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_solicitante_no_puede_crear_producto(self):
        """SOLICITANTE no puede crear productos"""
        # Login como solicitante
        response = self.client.post('/api/token/', {
            'username': 'solicitante',
            'password': 'Test@123'
        })
        
        token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        
        # Intentar crear producto
        response = self.client.post('/api/v1/productos/', {
            'clave': 'TEST-002',
            'descripcion': 'Producto de prueba',
            'unidad_medida': 'PIEZA',
            'precio_unitario': '10.00'
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
