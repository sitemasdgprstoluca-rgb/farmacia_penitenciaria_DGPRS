"""
Tests para el módulo de Productos
Cobertura: modelos, serializers, views, permisos
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, timedelta
from core.models import Producto, Centro, Lote
from core.constants import UNIDADES_MEDIDA

User = get_user_model()


class ProductoModelTest(TestCase):
    """Tests del modelo Producto"""
    
    def setUp(self):
        self.user_admin = User.objects.create_user(
            username='admin',
            password='test123',
            rol='admin_farmacia'
        )
        
        self.producto = Producto.objects.create(
            clave='MED001',
            descripcion='Paracetamol 500mg',
            unidad_medida='TABLETA',
            precio_unitario=Decimal('5.50'),
            stock_minimo=100,
            created_by=self.user_admin
        )
    
    def test_creacion_producto(self):
        """Test crear producto válido"""
        self.assertEqual(self.producto.clave, 'MED001')
        self.assertTrue(self.producto.activo)
    
    def test_normalizacion_clave(self):
        """Test que clave se normaliza a mayúsculas"""
        producto = Producto.objects.create(
            clave='med002',
            descripcion='Ibuprofeno 400mg',
            unidad_medida='TABLETA',
            precio_unitario=Decimal('8.00'),
            stock_minimo=50
        )
        self.assertEqual(producto.clave, 'MED002')
    
    def test_get_stock_actual_sin_lotes(self):
        """Test stock actual sin lotes"""
        self.assertEqual(self.producto.get_stock_actual(), 0)
    
    def test_get_stock_actual_con_lotes(self):
        """Test stock actual con lotes"""
        Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=80,
            estado='disponible'
        )
        Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE002',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=30,
            estado='disponible'
        )
        self.assertEqual(self.producto.get_stock_actual(), 110)
    
    def test_nivel_stock_critico(self):
        """Test nivel stock crítico"""
        Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=20,
            cantidad_actual=20,
            estado='disponible'
        )
        self.assertEqual(self.producto.get_nivel_stock(), 'critico')


class ProductoAPITest(APITestCase):
    """Tests de la API de productos"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Usuarios
        self.admin = User.objects.create_user(
            username='admin',
            password='admin123',
            rol='admin_farmacia'
        )
        self.user_normal = User.objects.create_user(
            username='user',
            password='user123',
            rol='usuario_normal'
        )
        
        # Producto de prueba
        self.producto = Producto.objects.create(
            clave='TEST001',
            descripcion='Producto de prueba',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=50
        )
    
    def test_listar_productos_sin_auth(self):
        """Test listar productos sin autenticación"""
        response = self.client.get('/api/productos/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_listar_productos_con_auth(self):
        """Test listar productos autenticado"""
        self.client.force_authenticate(user=self.user_normal)
        response = self.client.get('/api/productos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_crear_producto_sin_permisos(self):
        """Test crear producto sin permisos"""
        self.client.force_authenticate(user=self.user_normal)
        data = {
            'clave': 'NEW001',
            'descripcion': 'Nuevo producto',
            'unidad_medida': 'PIEZA',
            'precio_unitario': '15.00',
            'stock_minimo': 20
        }
        response = self.client.post('/api/productos/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_crear_producto_con_permisos(self):
        """Test crear producto con permisos admin"""
        self.client.force_authenticate(user=self.admin)
        data = {
            'clave': 'NEW001',
            'descripcion': 'Nuevo producto',
            'unidad_medida': 'PIEZA',
            'precio_unitario': '15.00',
            'stock_minimo': 20
        }
        response = self.client.post('/api/productos/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Producto.objects.count(), 2)
    
    def test_paginacion(self):
        """Test paginación de 25 items"""
        # Crear 30 productos
        for i in range(30):
            Producto.objects.create(
                clave=f'PROD{i:03d}',
                descripcion=f'Producto {i}',
                unidad_medida='PIEZA',
                precio_unitario=Decimal('10.00'),
                stock_minimo=10
            )
        
        self.client.force_authenticate(user=self.user_normal)
        response = self.client.get('/api/productos/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 25)
        self.assertIsNotNone(response.data['next'])
    
    def test_filtro_por_estado(self):
        """Test filtro por estado activo/inactivo"""
        Producto.objects.create(
            clave='INACTIVO',
            descripcion='Producto inactivo',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=False
        )
        
        self.client.force_authenticate(user=self.user_normal)
        
        # Solo activos
        response = self.client.get('/api/productos/?activo=true')
        self.assertEqual(response.data['count'], 1)
        
        # Solo inactivos
        response = self.client.get('/api/productos/?activo=false')
        self.assertEqual(response.data['count'], 1)
    
    def test_busqueda(self):
        """Test búsqueda por clave y descripción"""
        self.client.force_authenticate(user=self.user_normal)
        
        response = self.client.get('/api/productos/?search=TEST')
        self.assertEqual(response.data['count'], 1)
        
        response = self.client.get('/api/productos/?search=prueba')
        self.assertEqual(response.data['count'], 1)
