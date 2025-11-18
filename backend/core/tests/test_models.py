from django.test import TestCase
from django.core.exceptions import ValidationError
from core.models import User, Centro, Producto, Lote
from decimal import Decimal
from datetime import date, timedelta


class ProductoModelTest(TestCase):
    """Tests para modelo Producto"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_user',
            password='Test@123',
            email='test@test.com'
        )
    
    def test_crear_producto_valido(self):
        """Crear producto con datos válidos"""
        producto = Producto.objects.create(
            clave='MED-001',
            descripcion='Paracetamol 500mg',
            unidad_medida='pieza',
            precio_unitario=Decimal('10.50'),
            stock_minimo=100,
            created_by=self.user
        )
        
        self.assertEqual(producto.clave, 'MED-001')
        self.assertTrue(producto.activo)
        self.assertEqual(producto.get_stock_actual(), 0)
    
    def test_clave_normalizada(self):
        """La clave se normaliza a mayúsculas"""
        producto = Producto.objects.create(
            clave='med-002',
            descripcion='Ibuprofeno 400mg',
            unidad_medida='pieza',
            precio_unitario=Decimal('15.00')
        )
        
        self.assertEqual(producto.clave, 'MED-002')
    
    def test_clave_duplicada(self):
        """No se permite clave duplicada"""
        Producto.objects.create(
            clave='MED-003',
            descripcion='Producto 1',
            unidad_medida='pieza',
            precio_unitario=Decimal('10.00')
        )
        
        with self.assertRaises(Exception):
            Producto.objects.create(
                clave='MED-003',
                descripcion='Producto 2',
                unidad_medida='caja',
                precio_unitario=Decimal('20.00')
            )
    
    def test_precio_negativo(self):
        """No se permite precio negativo"""
        with self.assertRaises(ValidationError):
            producto = Producto(
                clave='MED-004',
                descripcion='Producto con precio negativo',
                unidad_medida='pieza',
                precio_unitario=Decimal('-10.00')
            )
            producto.full_clean()


class LoteModelTest(TestCase):
    """Tests para modelo Lote"""
    
    def setUp(self):
        self.producto = Producto.objects.create(
            clave='TEST-001',
            descripcion='Producto de prueba',
            unidad_medida='pieza',
            precio_unitario=Decimal('10.00')
        )
    
    def test_crear_lote_valido(self):
        """Crear lote con datos válidos"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-2024-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            proveedor='Proveedor Test'
        )
        
        self.assertEqual(lote.numero_lote, 'LOT-2024-001')
        self.assertEqual(lote.estado, 'disponible')
        self.assertFalse(lote.esta_caducado())
    
    def test_lote_vencido(self):
        """Lote con fecha pasada se marca como vencido"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-2020-001',
            fecha_caducidad=date.today() - timedelta(days=1),
            cantidad_inicial=100,
            cantidad_actual=50
        )
        
        self.assertEqual(lote.estado, 'vencido')
        self.assertTrue(lote.esta_caducado())
    
    def test_alerta_caducidad(self):
        """Test de niveles de alerta de caducidad"""
        # Lote próximo a caducar (15 días)
        lote_proximo = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-PROXIMO',
            fecha_caducidad=date.today() + timedelta(days=15),
            cantidad_inicial=50,
            cantidad_actual=50
        )
        
        self.assertEqual(lote_proximo.alerta_caducidad(), 'proximo')
        
        # Lote crítico (5 días)
        lote_critico = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-CRITICO',
            fecha_caducidad=date.today() + timedelta(days=5),
            cantidad_inicial=50,
            cantidad_actual=50
        )
        
        self.assertEqual(lote_critico.alerta_caducidad(), 'critico')
    
    def test_cantidad_actual_mayor_inicial(self):
        """No se permite cantidad actual > cantidad inicial"""
        with self.assertRaises(ValidationError):
            lote = Lote(
                producto=self.producto,
                numero_lote='LOT-INVALID',
                fecha_caducidad=date.today() + timedelta(days=100),
                cantidad_inicial=100,
                cantidad_actual=150
            )
            lote.full_clean()
