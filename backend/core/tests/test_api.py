from django.test import TestCase
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status
from core.models import User, Centro, Producto
from decimal import Decimal


class AuthenticationAPITest(TestCase):
    """Tests de autenticación JWT"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='Test@123',
            email='test@test.com'
        )
    
    def test_login_obtener_token(self):
        """Login correcto retorna access y refresh token"""
        response = self.client.post('/api/v1/token/', {
            'username': 'testuser',
            'password': 'Test@123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
    
    def test_login_credenciales_invalidas(self):
        """Login con contraseña incorrecta retorna 401"""
        response = self.client.post('/api/v1/token/', {
            'username': 'testuser',
            'password': 'WrongPassword'
        })
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_acceso_sin_token(self):
        """Endpoints protegidos requieren autenticación"""
        response = self.client.get('/api/v1/productos/')
        # Acepta 401 (not authenticated) o 403 (permission denied)
        # Ambos son correctos para endpoints protegidos sin credenciales
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])
    
    def test_acceso_con_token(self):
        """Acceso con token válido funciona"""
        # Obtener token
        login = self.client.post('/api/v1/token/', {
            'username': 'testuser',
            'password': 'Test@123'
        })
        token = login.data['access']
        
        # Usar token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/productos/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PermissionsAPITest(TestCase):
    """Tests de permisos por grupo"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Crear grupos
        self.grupo_farmaceutico = Group.objects.create(name='FARMACEUTICO')
        self.grupo_solicitante = Group.objects.create(name='SOLICITANTE')
        
        # Usuario FARMACEUTICO
        self.farmaceutico = User.objects.create_user(
            username='farmaceutico',
            password='Test@123'
        )
        self.farmaceutico.groups.add(self.grupo_farmaceutico)
        
        # Usuario SOLICITANTE
        self.solicitante = User.objects.create_user(
            username='solicitante',
            password='Test@123'
        )
        self.solicitante.groups.add(self.grupo_solicitante)
    
    def test_farmaceutico_puede_crear_producto(self):
        """FARMACEUTICO puede crear productos"""
        # Login
        login = self.client.post('/api/v1/token/', {
            'username': 'farmaceutico',
            'password': 'Test@123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        
        # Crear producto
        response = self.client.post('/api/v1/productos/', {
            'clave': 'TEST-001',
            'descripcion': 'Producto de prueba para farmaceutico',
            'unidad_medida': 'PIEZA',
            'precio_unitario': '10.00',
            'stock_minimo': 50
        })
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['clave'], 'TEST-001')
    
    def test_solicitante_no_puede_crear_producto(self):
        """SOLICITANTE no puede crear productos"""
        # Login
        login = self.client.post('/api/v1/token/', {
            'username': 'solicitante',
            'password': 'Test@123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        
        # Intentar crear producto
        response = self.client.post('/api/v1/productos/', {
            'clave': 'TEST-002',
            'descripcion': 'Producto de prueba',
            'unidad_medida': 'PIEZA',
            'precio_unitario': '10.00'
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ProductoAPITest(TestCase):
    """Tests de endpoints de Producto"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Usuario con permisos
        grupo = Group.objects.create(name='FARMACEUTICO')
        self.user = User.objects.create_user(
            username='farmaceutico',
            password='Test@123'
        )
        self.user.groups.add(grupo)
        
        # Login
        login = self.client.post('/api/v1/token/', {
            'username': 'farmaceutico',
            'password': 'Test@123'
        })
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login.data["access"]}')
        
        # Crear productos de prueba
        Producto.objects.create(
            clave='PARACETAMOL',
            descripcion='Paracetamol 500mg',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('5.50'),
            stock_minimo=100
        )
    
    def test_listar_productos(self):
        """Listar productos retorna resultados paginados"""
        response = self.client.get('/api/v1/productos/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertGreater(len(response.data['results']), 0)
    
    def test_filtrar_por_activo(self):
        """Filtrar productos activos"""
        response = self.client.get('/api/v1/productos/?activo=true')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for producto in response.data['results']:
            self.assertTrue(producto['activo'])
    
    def test_buscar_por_clave(self):
        """Buscar producto por clave"""
        response = self.client.get('/api/v1/productos/?search=PARACETAMOL')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        self.assertIn('PARACETAMOL', response.data['results'][0]['clave'])
