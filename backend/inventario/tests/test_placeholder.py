"""
Tests para el módulo de inventario - ISS-004 FIX

Cobertura:
- ISS-001: get_stock_actual() excluye deleted_at y lotes vencidos
- ISS-002: Validación de fechas con timezone-aware dates
- Nivel de stock (critico, bajo, normal, alto)
- Validación de lotes
"""
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal

from core.models import Centro, Producto, Lote

User = get_user_model()


class StockCalculationTests(TestCase):
    """
    ISS-001: Tests para verificar que get_stock_actual() excluye:
    - Lotes con deleted_at (soft-deleted)
    - Lotes con fecha_caducidad vencida
    - Lotes con estado diferente a 'disponible'
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_stock',
            email='admin@stock.test',
            password='Admin@123'
        )
        cls.producto = Producto.objects.create(
            clave='STOCK-TEST-001',
            descripcion='Producto para pruebas de stock',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=50,
            activo=True
        )
    
    def test_stock_excluye_lotes_deleted(self):
        """ISS-001: get_stock_actual() debe excluir lotes soft-deleted"""
        # Crear lote activo
        lote_activo = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-ACTIVO-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Crear lote soft-deleted
        lote_deleted = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-DELETED-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible',
            deleted_at=timezone.now()  # Soft-deleted
        )
        
        # Stock debe ser solo del lote activo (100)
        self.assertEqual(self.producto.get_stock_actual(), 100)
    
    def test_stock_excluye_lotes_vencidos(self):
        """ISS-001: get_stock_actual() debe excluir lotes vencidos"""
        # Crear lote vigente
        lote_vigente = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-VIGENTE-001',
            fecha_caducidad=date.today() + timedelta(days=30),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Crear lote vencido (fecha pasada pero estado aún 'disponible')
        lote_vencido = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-VENCIDO-001',
            fecha_caducidad=date.today() - timedelta(days=1),
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible'  # Estado no actualizado aún
        )
        
        # Stock debe ser solo del lote vigente (100)
        self.assertEqual(self.producto.get_stock_actual(), 100)
    
    def test_stock_excluye_lotes_no_disponibles(self):
        """get_stock_actual() debe excluir lotes con estado != 'disponible'"""
        # Crear lote disponible
        lote_disponible = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-DISP-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Crear lote agotado
        lote_agotado = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-AGOT-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=0,
            estado='agotado'
        )
        
        # Stock debe ser solo del lote disponible (100)
        self.assertEqual(self.producto.get_stock_actual(), 100)
    
    def test_stock_suma_multiples_lotes_validos(self):
        """get_stock_actual() debe sumar todos los lotes válidos"""
        # Crear múltiples lotes válidos
        for i in range(3):
            Lote.objects.create(
                producto=self.producto,
                numero_lote=f'LOTE-MULTI-{i:03d}',
                fecha_caducidad=date.today() + timedelta(days=365),
                cantidad_inicial=100,
                cantidad_actual=100,
                estado='disponible'
            )
        
        # Stock debe ser la suma de todos (300)
        self.assertEqual(self.producto.get_stock_actual(), 300)
    
    def test_stock_cero_sin_lotes(self):
        """get_stock_actual() debe retornar 0 si no hay lotes válidos"""
        producto_sin_lotes = Producto.objects.create(
            clave='PROD-SIN-LOTES',
            descripcion='Producto sin lotes',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('5.00'),
            stock_minimo=10,
            activo=True
        )
        
        self.assertEqual(producto_sin_lotes.get_stock_actual(), 0)


class LoteExpirationTests(TestCase):
    """
    ISS-002: Tests para validación de fechas de caducidad
    con timezone-aware dates
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_exp',
            email='admin@exp.test',
            password='Admin@123'
        )
        cls.producto = Producto.objects.create(
            clave='EXP-TEST-001',
            descripcion='Producto para pruebas de caducidad',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=50,
            activo=True
        )
    
    def test_lote_vencido_marca_estado_vencido(self):
        """ISS-002: Lote con fecha pasada debe marcarse como 'vencido'"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-VENC-001',
            fecha_caducidad=date.today() - timedelta(days=1),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        lote.full_clean()  # Dispara clean()
        
        self.assertEqual(lote.estado, 'vencido')
    
    def test_dias_para_caducar_futuro(self):
        """ISS-002: dias_para_caducar() con fecha futura"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-FUT-001',
            fecha_caducidad=date.today() + timedelta(days=30),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        self.assertEqual(lote.dias_para_caducar(), 30)
    
    def test_dias_para_caducar_pasado(self):
        """ISS-002: dias_para_caducar() con fecha pasada retorna negativo"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-PAS-001',
            fecha_caducidad=date.today() - timedelta(days=10),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        self.assertEqual(lote.dias_para_caducar(), -10)
    
    def test_esta_caducado_true(self):
        """ISS-002: esta_caducado() retorna True para lotes vencidos"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-CAD-001',
            fecha_caducidad=date.today() - timedelta(days=1),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        self.assertTrue(lote.esta_caducado())
    
    def test_esta_caducado_false(self):
        """ISS-002: esta_caducado() retorna False para lotes vigentes"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-VIG-001',
            fecha_caducidad=date.today() + timedelta(days=30),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        self.assertFalse(lote.esta_caducado())


class NivelStockTests(TestCase):
    """
    Tests para get_nivel_stock() - clasificación de niveles
    según constantes NIVELES_STOCK
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_nivel',
            email='admin@nivel.test',
            password='Admin@123'
        )
    
    def test_nivel_critico(self):
        """Stock <= 25% del mínimo = crítico"""
        producto = Producto.objects.create(
            clave='NIVEL-CRIT-001',
            descripcion='Producto nivel crítico',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=100,
            activo=True
        )
        # 25% de 100 = 25, crear lote con 10 unidades
        Lote.objects.create(
            producto=producto,
            numero_lote='LOTE-CRIT-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=10,
            cantidad_actual=10,
            estado='disponible'
        )
        
        self.assertEqual(producto.get_nivel_stock(), 'critico')
    
    def test_nivel_bajo(self):
        """Stock entre 25% y 50% del mínimo = bajo"""
        producto = Producto.objects.create(
            clave='NIVEL-BAJO-001',
            descripcion='Producto nivel bajo',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=100,
            activo=True
        )
        # 50% de 100 = 50, crear lote con 40 unidades (40% está entre 25% y 50%)
        Lote.objects.create(
            producto=producto,
            numero_lote='LOTE-BAJO-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=40,
            cantidad_actual=40,
            estado='disponible'
        )
        
        self.assertEqual(producto.get_nivel_stock(), 'bajo')
    
    def test_nivel_normal(self):
        """Stock entre 50% y 100% del mínimo = normal"""
        producto = Producto.objects.create(
            clave='NIVEL-NORM-001',
            descripcion='Producto nivel normal',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=100,
            activo=True
        )
        # 100% de 100 = 100, crear lote con 80 unidades (80% está entre 50% y 100%)
        Lote.objects.create(
            producto=producto,
            numero_lote='LOTE-NORM-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=80,
            cantidad_actual=80,
            estado='disponible'
        )
        
        self.assertEqual(producto.get_nivel_stock(), 'normal')
    
    def test_nivel_alto(self):
        """Stock > 100% del mínimo = alto"""
        producto = Producto.objects.create(
            clave='NIVEL-ALTO-001',
            descripcion='Producto nivel alto',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=100,
            activo=True
        )
        # Más de 100% del mínimo
        Lote.objects.create(
            producto=producto,
            numero_lote='LOTE-ALTO-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=200,
            cantidad_actual=200,
            estado='disponible'
        )
        
        self.assertEqual(producto.get_nivel_stock(), 'alto')


class LoteValidationTests(TestCase):
    """
    Tests para validaciones del modelo Lote
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_val',
            email='admin@val.test',
            password='Admin@123'
        )
        cls.producto = Producto.objects.create(
            clave='VAL-TEST-001',
            descripcion='Producto para pruebas de validación',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=50,
            activo=True
        )
        cls.centro = Centro.objects.create(
            clave='CENT-VAL-001',
            nombre='Centro de Validación',
            direccion='Dirección de prueba',
            telefono='555-0000',
            activo=True
        )
    
    def test_cantidad_actual_no_excede_inicial(self):
        """Cantidad actual no puede ser mayor a cantidad inicial"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-EXC-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=150,  # Excede inicial
            estado='disponible'
        )
        
        with self.assertRaises(ValidationError) as ctx:
            lote.full_clean()
        
        self.assertIn('cantidad_actual', ctx.exception.message_dict)
    
    def test_numero_lote_min_length(self):
        """Número de lote debe tener mínimo de caracteres (LOTE_NUMERO_MIN_LENGTH=2)"""
        lote = Lote(
            producto=self.producto,
            numero_lote='A',  # 1 char - below minimum of 2
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        with self.assertRaises(ValidationError) as ctx:
            lote.full_clean()
        
        self.assertIn('numero_lote', ctx.exception.message_dict)
    
    def test_numero_lote_normalizado_mayusculas(self):
        """Número de lote debe normalizarse a mayúsculas"""
        lote = Lote(
            producto=self.producto,
            numero_lote='lote-minusculas',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        lote.full_clean()
        
        self.assertEqual(lote.numero_lote, 'LOTE-MINUSCULAS')
    
    def test_lote_agotado_automatico(self):
        """Lote con cantidad_actual=0 debe marcarse como 'agotado'"""
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTE-AGOT-AUTO',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=0,
            estado='disponible'
        )
        lote.full_clean()
        
        self.assertEqual(lote.estado, 'agotado')
    
    def test_lote_centro_requiere_lote_origen(self):
        """Lote en centro debe tener lote_origen de farmacia"""
        lote = Lote(
            producto=self.producto,
            centro=self.centro,  # Lote en centro
            numero_lote='LOTE-SIN-ORIG',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible',
            lote_origen=None  # Sin origen
        )
        
        with self.assertRaises(ValidationError) as ctx:
            lote.full_clean()
        
        self.assertIn('lote_origen', ctx.exception.message_dict)
    
    def test_lote_farmacia_sin_lote_origen(self):
        """Lote en farmacia (centro=None) NO debe tener lote_origen"""
        # Crear lote farmacia válido
        lote_farmacia = Lote.objects.create(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-FARM-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Intentar asignar lote_origen (no permitido)
        lote_farmacia.lote_origen = lote_farmacia  # Self-reference
        
        with self.assertRaises(ValidationError) as ctx:
            lote_farmacia.full_clean()
        
        self.assertIn('lote_origen', ctx.exception.message_dict)


class AlertaCaducidadTests(TestCase):
    """
    Tests para alerta_caducidad() - clasificación según SIFP
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_alert',
            email='admin@alert.test',
            password='Admin@123'
        )
        cls.producto = Producto.objects.create(
            clave='ALERT-TEST-001',
            descripcion='Producto para pruebas de alertas',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=50,
            activo=True
        )
    
    def test_alerta_vencido(self):
        """Lote vencido debe retornar 'vencido'"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-ALERT-VEN',
            fecha_caducidad=date.today() - timedelta(days=1),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        self.assertEqual(lote.alerta_caducidad(), 'vencido')
    
    def test_alerta_critico(self):
        """Lote < 90 días = crítico"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-ALERT-CRI',
            fecha_caducidad=date.today() + timedelta(days=60),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        self.assertEqual(lote.alerta_caducidad(), 'critico')
    
    def test_alerta_proximo(self):
        """Lote 90-180 días = próximo"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-ALERT-PRO',
            fecha_caducidad=date.today() + timedelta(days=120),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        self.assertEqual(lote.alerta_caducidad(), 'proximo')
    
    def test_alerta_normal(self):
        """Lote > 180 días = normal"""
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-ALERT-NOR',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        self.assertEqual(lote.alerta_caducidad(), 'normal')
