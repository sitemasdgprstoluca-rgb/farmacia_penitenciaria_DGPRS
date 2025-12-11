"""
ISS-001/003/004: Tests para lote_helpers.py

Cubre:
- LoteQueryHelper.get_lotes_disponibles()
- LoteQueryHelper.validar_stock_surtido()
- LoteQueryHelper.seleccionar_lotes_fefo()
- ContratoValidator.validar_entrada_contrato()
"""
import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.utils import timezone

# Import after Django setup
try:
    from core.lote_helpers import LoteQueryHelper, ContratoValidator
    from core.models import Lote, Producto, Centro
except ImportError:
    # En caso de que Django no esté configurado
    pass


class LoteQueryHelperTests(TestCase):
    """Tests para LoteQueryHelper."""
    
    @classmethod
    def setUpTestData(cls):
        """Setup inicial de datos de prueba."""
        # Crear producto de prueba
        cls.producto = Producto.objects.create(
            clave='TEST-001',
            nombre='Producto Test',
            unidad_medida='pieza',
            stock_minimo=10,
        )
        
        # Crear centro de prueba
        cls.centro = Centro.objects.create(
            nombre='Centro Test',
            clave='CT001',
        )
        
        hoy = timezone.now().date()
        
        # Lote disponible en farmacia central
        cls.lote_disponible = Lote.objects.create(
            numero_lote='LOT-001',
            producto=cls.producto,
            cantidad_inicial=100,
            cantidad_actual=80,
            fecha_caducidad=hoy + timedelta(days=180),
            activo=True,
            centro=None,  # Farmacia central
        )
        
        # Lote vencido
        cls.lote_vencido = Lote.objects.create(
            numero_lote='LOT-002',
            producto=cls.producto,
            cantidad_inicial=50,
            cantidad_actual=50,
            fecha_caducidad=hoy - timedelta(days=10),
            activo=True,
            centro=None,
        )
        
        # Lote agotado
        cls.lote_agotado = Lote.objects.create(
            numero_lote='LOT-003',
            producto=cls.producto,
            cantidad_inicial=30,
            cantidad_actual=0,
            fecha_caducidad=hoy + timedelta(days=90),
            activo=True,
            centro=None,
        )
        
        # Lote inactivo
        cls.lote_inactivo = Lote.objects.create(
            numero_lote='LOT-004',
            producto=cls.producto,
            cantidad_inicial=40,
            cantidad_actual=40,
            fecha_caducidad=hoy + timedelta(days=120),
            activo=False,
            centro=None,
        )
        
        # Lote en centro (no farmacia central)
        cls.lote_en_centro = Lote.objects.create(
            numero_lote='LOT-005',
            producto=cls.producto,
            cantidad_inicial=60,
            cantidad_actual=60,
            fecha_caducidad=hoy + timedelta(days=150),
            activo=True,
            centro=cls.centro,
        )
    
    def test_get_lotes_disponibles_solo_farmacia_central(self):
        """Solo debe retornar lotes de farmacia central activos, con stock y no vencidos."""
        lotes = LoteQueryHelper.get_lotes_disponibles(
            producto=self.producto,
            solo_farmacia_central=True,
        )
        
        lotes_ids = list(lotes.values_list('id', flat=True))
        
        # Solo debe incluir el lote disponible
        self.assertIn(self.lote_disponible.id, lotes_ids)
        self.assertNotIn(self.lote_vencido.id, lotes_ids)
        self.assertNotIn(self.lote_agotado.id, lotes_ids)
        self.assertNotIn(self.lote_inactivo.id, lotes_ids)
        self.assertNotIn(self.lote_en_centro.id, lotes_ids)
    
    def test_get_lotes_disponibles_incluye_centro(self):
        """Debe incluir lotes de centro cuando no se filtra por farmacia central."""
        lotes = LoteQueryHelper.get_lotes_disponibles(
            producto=self.producto,
            solo_farmacia_central=False,
        )
        
        lotes_ids = list(lotes.values_list('id', flat=True))
        
        # Debe incluir lote disponible y lote en centro
        self.assertIn(self.lote_disponible.id, lotes_ids)
        self.assertIn(self.lote_en_centro.id, lotes_ids)
    
    def test_get_stock_disponible_farmacia_central(self):
        """Calcula correctamente el stock disponible en farmacia central."""
        stock = LoteQueryHelper.get_stock_disponible(
            producto=self.producto,
            solo_farmacia_central=True,
        )
        
        # Solo cuenta lote_disponible (80 unidades)
        self.assertEqual(stock, 80)
    
    def test_validar_stock_surtido_suficiente(self):
        """Valida correctamente cuando hay stock suficiente."""
        resultado = LoteQueryHelper.validar_stock_surtido(
            producto=self.producto,
            cantidad_requerida=50,
            solo_farmacia_central=True,
        )
        
        self.assertTrue(resultado['valido'])
        self.assertEqual(resultado['stock_disponible'], 80)
        self.assertEqual(resultado['faltante'], 0)
        self.assertEqual(len(resultado['errores']), 0)
    
    def test_validar_stock_surtido_insuficiente(self):
        """Detecta correctamente cuando no hay stock suficiente."""
        resultado = LoteQueryHelper.validar_stock_surtido(
            producto=self.producto,
            cantidad_requerida=100,
            solo_farmacia_central=True,
        )
        
        self.assertFalse(resultado['valido'])
        self.assertEqual(resultado['stock_disponible'], 80)
        self.assertEqual(resultado['faltante'], 20)
        self.assertGreater(len(resultado['errores']), 0)
    
    def test_seleccionar_lotes_fefo(self):
        """Selecciona lotes correctamente usando FEFO."""
        # Crear lote con caducidad más próxima
        hoy = timezone.now().date()
        lote_proximo = Lote.objects.create(
            numero_lote='LOT-FEFO',
            producto=self.producto,
            cantidad_inicial=30,
            cantidad_actual=30,
            fecha_caducidad=hoy + timedelta(days=30),
            activo=True,
            centro=None,
        )
        
        seleccion = LoteQueryHelper.seleccionar_lotes_fefo(
            producto=self.producto,
            cantidad_requerida=50,
            solo_farmacia_central=True,
        )
        
        # El primero debe ser el lote más próximo a vencer
        self.assertEqual(seleccion[0]['lote_id'], lote_proximo.id)
        self.assertEqual(seleccion[0]['cantidad_a_usar'], 30)
        
        # El segundo debe ser el lote disponible
        self.assertEqual(seleccion[1]['lote_id'], self.lote_disponible.id)
        self.assertEqual(seleccion[1]['cantidad_a_usar'], 20)
        
        # Cleanup
        lote_proximo.delete()


class ContratoValidatorTests(TestCase):
    """Tests para ContratoValidator."""
    
    def setUp(self):
        """Setup de datos de prueba."""
        self.producto = Producto.objects.create(
            clave='TEST-CV-001',
            nombre='Producto Contrato',
            unidad_medida='pieza',
            stock_minimo=5,
        )
        
        hoy = timezone.now().date()
        
        self.lote = Lote.objects.create(
            numero_lote='LOT-CV-001',
            producto=self.producto,
            cantidad_inicial=100,
            cantidad_actual=50,
            fecha_caducidad=hoy + timedelta(days=200),
            activo=True,
            numero_contrato='CONT-2024-001',
        )
    
    def test_validar_entrada_con_contrato(self):
        """Entrada con contrato válido debe pasar."""
        resultado = ContratoValidator.validar_entrada_contrato(
            lote=self.lote,
            cantidad_a_ingresar=10,
            es_entrada_formal=True,
            strict=False,
        )
        
        self.assertTrue(resultado['valido'])
        self.assertEqual(len(resultado['errores']), 0)
    
    def test_validar_entrada_sin_contrato_formal(self):
        """Entrada formal sin contrato debe fallar en modo estricto."""
        # Crear lote sin contrato
        hoy = timezone.now().date()
        lote_sin_contrato = Lote.objects.create(
            numero_lote='LOT-CV-002',
            producto=self.producto,
            cantidad_inicial=50,
            cantidad_actual=0,
            fecha_caducidad=hoy + timedelta(days=180),
            activo=True,
            numero_contrato=None,
        )
        
        resultado = ContratoValidator.validar_entrada_contrato(
            lote=lote_sin_contrato,
            cantidad_a_ingresar=10,
            es_entrada_formal=True,
            strict=True,
        )
        
        self.assertFalse(resultado['valido'])
        self.assertGreater(len(resultado['errores']), 0)
        
        # Cleanup
        lote_sin_contrato.delete()
    
    def test_validar_lote_vencido_para_entrada(self):
        """No debe permitir entradas a lotes vencidos."""
        hoy = timezone.now().date()
        lote_vencido = Lote.objects.create(
            numero_lote='LOT-CV-VEN',
            producto=self.producto,
            cantidad_inicial=50,
            cantidad_actual=30,
            fecha_caducidad=hoy - timedelta(days=10),
            activo=True,
            numero_contrato='CONT-2024-002',
        )
        
        resultado = ContratoValidator.validar_entrada_contrato(
            lote=lote_vencido,
            cantidad_a_ingresar=10,
            es_entrada_formal=True,
            strict=True,
        )
        
        self.assertFalse(resultado['valido'])
        self.assertTrue(any('vencido' in e.lower() for e in resultado['errores']))
        
        # Cleanup
        lote_vencido.delete()
    
    def test_validar_excedente_cantidad(self):
        """Detecta excedente sobre cantidad inicial."""
        resultado = ContratoValidator.validar_entrada_contrato(
            lote=self.lote,
            cantidad_a_ingresar=70,  # 50 + 70 = 120, excede 100 * 1.1 = 110
            es_entrada_formal=True,
            strict=True,
        )
        
        self.assertFalse(resultado['valido'])
        self.assertTrue(any('excede' in e.lower() for e in resultado['errores']))
    
    def test_validar_lote_para_surtido(self):
        """Valida lote para surtido correctamente."""
        resultado = ContratoValidator.validar_lote_para_surtido(
            lote=self.lote,
            cantidad_a_surtir=30,
        )
        
        self.assertTrue(resultado['valido'])
        self.assertEqual(len(resultado['errores']), 0)
    
    def test_validar_lote_insuficiente_para_surtido(self):
        """Detecta stock insuficiente para surtido."""
        resultado = ContratoValidator.validar_lote_para_surtido(
            lote=self.lote,
            cantidad_a_surtir=100,  # Solo hay 50
        )
        
        self.assertFalse(resultado['valido'])
        self.assertTrue(any('insuficiente' in e.lower() or 'suficiente' in e.lower() for e in resultado['errores']))


class LoteQueryHelperEdgeCasesTests(TestCase):
    """Tests para casos borde de LoteQueryHelper."""
    
    def setUp(self):
        self.producto = Producto.objects.create(
            clave='TEST-EDGE-001',
            nombre='Producto Edge',
            unidad_medida='pieza',
            stock_minimo=5,
        )
    
    def test_get_lotes_disponibles_sin_producto(self):
        """Debe retornar todos los lotes disponibles si no se filtra por producto."""
        lotes = LoteQueryHelper.get_lotes_disponibles()
        # No debe lanzar excepción
        self.assertIsNotNone(lotes)
    
    def test_validar_stock_producto_sin_lotes(self):
        """Valida correctamente cuando no hay lotes."""
        resultado = LoteQueryHelper.validar_stock_surtido(
            producto=self.producto,
            cantidad_requerida=10,
            solo_farmacia_central=True,
        )
        
        self.assertFalse(resultado['valido'])
        self.assertEqual(resultado['stock_disponible'], 0)
        self.assertEqual(resultado['faltante'], 10)
    
    def test_seleccionar_lotes_fefo_sin_stock(self):
        """Retorna lista vacía cuando no hay stock."""
        seleccion = LoteQueryHelper.seleccionar_lotes_fefo(
            producto=self.producto,
            cantidad_requerida=10,
            solo_farmacia_central=True,
        )
        
        self.assertEqual(len(seleccion), 0)
