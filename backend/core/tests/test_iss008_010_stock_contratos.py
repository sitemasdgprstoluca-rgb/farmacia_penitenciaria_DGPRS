"""
Tests para ISS-008 y ISS-010

ISS-008: Stock comprometido - Cálculo de stock reservado por requisiciones pendientes
ISS-010: Control de contratos - Trazabilidad por número de contrato
"""
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.models import Centro, Producto, Lote, Requisicion, DetalleRequisicion

User = get_user_model()


class BaseTestCase(TestCase):
    """Base con fixtures comunes para ISS-008 e ISS-010"""
    
    @classmethod
    def setUpTestData(cls):
        """Crear datos de prueba una vez para toda la clase"""
        cls.user = User.objects.create_user(
            username='test_stock',
            email='test@test.com',
            password='testpass123!',
            rol='farmacia'
        )
        cls.centro = Centro.objects.create(
            clave='CTR001',
            nombre='Centro Test',
            direccion='Test Address'
        )
        cls.producto = Producto.objects.create(
            clave='MED001',
            descripcion='Medicamento Test',
            unidad_medida='PIEZA',
            stock_minimo=10,
            precio_unitario=Decimal('10.00')
        )
        cls.producto2 = Producto.objects.create(
            clave='MED002',
            descripcion='Medicamento Test 2',
            unidad_medida='PIEZA',
            stock_minimo=5,
            precio_unitario=Decimal('15.00')
        )


class ISS008StockComprometidoTest(BaseTestCase):
    """ISS-008: Tests de cálculo de stock comprometido"""
    
    def setUp(self):
        """Crear lotes frescos para cada test"""
        self.lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
    
    def test_stock_comprometido_sin_requisiciones(self):
        """Sin requisiciones pendientes, stock comprometido = 0"""
        comprometido = self.producto.get_stock_comprometido()
        self.assertEqual(comprometido, 0)
    
    def test_stock_comprometido_requisicion_autorizada(self):
        """Requisiciones autorizadas comprometen stock"""
        # Crear requisición autorizada
        req = Requisicion.objects.create(
            folio='REQ-TEST-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=20,
            cantidad_autorizada=15  # Autorizado parcialmente
        )
        
        comprometido = self.producto.get_stock_comprometido()
        self.assertEqual(comprometido, 15)  # Cantidad autorizada
    
    def test_stock_comprometido_requisicion_parcial(self):
        """Requisiciones parciales también comprometen stock"""
        req = Requisicion.objects.create(
            folio='REQ-TEST-002',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='parcial'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=30,
            cantidad_autorizada=25,
            cantidad_surtida=10  # Ya se surtieron 10
        )
        
        # Comprometido = autorizado - surtido = 25 - 10 = 15
        comprometido = self.producto.get_stock_comprometido()
        self.assertEqual(comprometido, 15)
    
    def test_stock_comprometido_requisicion_surtida(self):
        """Requisiciones surtidas (pendientes de recibir) también comprometen"""
        req = Requisicion.objects.create(
            folio='REQ-TEST-003',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='surtida'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=20,
            cantidad_autorizada=20,
            cantidad_surtida=20  # Todo surtido
        )
        
        # Surtida completamente = 0 comprometido adicional
        comprometido = self.producto.get_stock_comprometido()
        self.assertEqual(comprometido, 0)
    
    def test_stock_comprometido_excluye_recibidas(self):
        """Requisiciones recibidas NO comprometen stock"""
        req = Requisicion.objects.create(
            folio='REQ-TEST-004',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='recibida'  # Ya recibida
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=50,
            cantidad_autorizada=50,
            cantidad_surtida=50
        )
        
        comprometido = self.producto.get_stock_comprometido()
        self.assertEqual(comprometido, 0)
    
    def test_stock_comprometido_excluye_borrador_enviada(self):
        """Borradores y enviadas NO comprometen stock (no autorizadas)"""
        req1 = Requisicion.objects.create(
            folio='REQ-BORR-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='borrador'
        )
        DetalleRequisicion.objects.create(
            requisicion=req1,
            producto=self.producto,
            cantidad_solicitada=30,
            cantidad_autorizada=0
        )
        
        req2 = Requisicion.objects.create(
            folio='REQ-ENV-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='enviada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req2,
            producto=self.producto,
            cantidad_solicitada=20,
            cantidad_autorizada=0
        )
        
        comprometido = self.producto.get_stock_comprometido()
        self.assertEqual(comprometido, 0)
    
    def test_stock_disponible_real(self):
        """get_stock_disponible_real descuenta comprometido"""
        # Stock actual = 100
        req = Requisicion.objects.create(
            folio='REQ-REAL-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=30,
            cantidad_autorizada=25
        )
        
        stock_actual = self.producto.get_stock_actual()  # 100
        stock_comprometido = self.producto.get_stock_comprometido()  # 25
        stock_disponible = self.producto.get_stock_disponible_real()  # 75
        
        self.assertEqual(stock_actual, 100)
        self.assertEqual(stock_comprometido, 25)
        self.assertEqual(stock_disponible, 75)
    
    def test_resumen_stock_completo(self):
        """get_resumen_stock retorna info completa"""
        req = Requisicion.objects.create(
            folio='REQ-RES-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=20,
            cantidad_autorizada=15
        )
        
        resumen = self.producto.get_resumen_stock()
        
        self.assertEqual(resumen['stock_actual'], 100)
        self.assertEqual(resumen['stock_comprometido'], 15)
        self.assertEqual(resumen['stock_disponible'], 85)
        self.assertTrue(resumen['tiene_comprometido'])
        self.assertIn(resumen['nivel_stock'], ['critico', 'bajo', 'normal', 'alto'])
    
    def test_multiples_requisiciones_suman_comprometido(self):
        """Múltiples requisiciones pendientes suman su comprometido"""
        # Requisición 1: 10 autorizados
        req1 = Requisicion.objects.create(
            folio='REQ-MULT-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req1,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=15,
            cantidad_autorizada=10
        )
        
        # Requisición 2: 20 autorizados
        req2 = Requisicion.objects.create(
            folio='REQ-MULT-002',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req2,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=25,
            cantidad_autorizada=20
        )
        
        comprometido = self.producto.get_stock_comprometido()
        self.assertEqual(comprometido, 30)  # 10 + 20


class ISS010ControlContratosTest(BaseTestCase):
    """ISS-010: Tests de control y trazabilidad de contratos"""
    
    def setUp(self):
        """Crear lotes con diferentes contratos"""
        self.lote_con_contrato = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-CON-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=80,
            estado='disponible',
            numero_contrato='CONT-2024-001',
            proveedor='Proveedor ABC',
            factura='FAC-001',
            marca='MarcaX',
            precio_compra=Decimal('50.00')
        )
        self.lote_sin_contrato = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-SIN-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible'
        )
    
    def test_tiene_contrato(self):
        """tiene_contrato() detecta correctamente"""
        self.assertTrue(self.lote_con_contrato.tiene_contrato())
        self.assertFalse(self.lote_sin_contrato.tiene_contrato())
    
    def test_tiene_contrato_vacio_es_false(self):
        """String vacío o espacios = sin contrato"""
        lote_vacio = Lote.objects.create(
            producto=self.producto2,
            numero_lote='LOT-VAC-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=10,
            cantidad_actual=10,
            estado='disponible',
            numero_contrato='   '  # Solo espacios
        )
        self.assertFalse(lote_vacio.tiene_contrato())
    
    def test_get_info_contrato_completa(self):
        """get_info_contrato() retorna datos completos"""
        info = self.lote_con_contrato.get_info_contrato()
        
        self.assertTrue(info['tiene_contrato'])
        self.assertEqual(info['numero_contrato'], 'CONT-2024-001')
        self.assertEqual(info['proveedor'], 'Proveedor ABC')
        self.assertEqual(info['factura'], 'FAC-001')
        self.assertEqual(info['marca'], 'MarcaX')
        self.assertEqual(info['precio_compra'], Decimal('50.00'))
    
    def test_get_info_contrato_sin_contrato(self):
        """get_info_contrato() para lote sin contrato"""
        info = self.lote_sin_contrato.get_info_contrato()
        
        self.assertFalse(info['tiene_contrato'])
        self.assertIsNone(info['numero_contrato'])
    
    def test_por_contrato(self):
        """por_contrato() filtra correctamente"""
        # Crear otro lote con mismo contrato
        Lote.objects.create(
            producto=self.producto2,
            numero_lote='LOT-CON-002',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=75,
            cantidad_actual=75,
            estado='disponible',
            numero_contrato='CONT-2024-001'
        )
        
        lotes = Lote.por_contrato('CONT-2024-001')
        self.assertEqual(lotes.count(), 2)
    
    def test_por_contrato_excluye_eliminados(self):
        """por_contrato() excluye soft-deleted por defecto"""
        self.lote_con_contrato.soft_delete()
        
        lotes = Lote.por_contrato('CONT-2024-001', solo_disponibles=True)
        self.assertEqual(lotes.count(), 0)
        
        lotes_todos = Lote.por_contrato('CONT-2024-001', solo_disponibles=False)
        self.assertEqual(lotes_todos.count(), 1)
    
    def test_resumen_por_contrato(self):
        """resumen_por_contrato() genera estadísticas correctas"""
        # Agregar otro lote al mismo contrato
        Lote.objects.create(
            producto=self.producto2,
            numero_lote='LOT-CON-003',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=30,
            estado='disponible',
            numero_contrato='CONT-2024-001',
            precio_compra=Decimal('25.00')
        )
        
        resumen = Lote.resumen_por_contrato('CONT-2024-001')
        
        self.assertEqual(resumen['numero_contrato'], 'CONT-2024-001')
        self.assertEqual(resumen['total_lotes'], 2)
        self.assertEqual(resumen['total_cantidad_inicial'], 150)  # 100 + 50
        self.assertEqual(resumen['total_cantidad_actual'], 110)  # 80 + 30
        self.assertEqual(resumen['cantidad_consumida'], 40)  # 150 - 110
        self.assertIn('MED001', resumen['productos'])
        self.assertIn('MED002', resumen['productos'])
        # Valor = 100*50 + 50*25 = 5000 + 1250 = 6250
        self.assertEqual(resumen['valor_total'], Decimal('6250.00'))
    
    def test_resumen_por_contrato_inexistente(self):
        """resumen_por_contrato() para contrato sin lotes"""
        resumen = Lote.resumen_por_contrato('CONT-NO-EXISTE')
        
        self.assertEqual(resumen['total_lotes'], 0)
        self.assertEqual(resumen['total_cantidad_inicial'], 0)
        self.assertEqual(resumen['productos'], [])
    
    def test_contratos_activos(self):
        """contratos_activos() lista contratos únicos"""
        # Crear lotes con diferentes contratos
        Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-ACT-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=10,
            cantidad_actual=10,
            estado='disponible',
            numero_contrato='CONT-2024-002'
        )
        Lote.objects.create(
            producto=self.producto2,
            numero_lote='LOT-ACT-002',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=10,
            cantidad_actual=10,
            estado='disponible',
            numero_contrato='CONT-2024-003'
        )
        
        contratos = Lote.contratos_activos()
        
        self.assertIn('CONT-2024-001', contratos)
        self.assertIn('CONT-2024-002', contratos)
        self.assertIn('CONT-2024-003', contratos)
        # Sin duplicados
        self.assertEqual(len(contratos), len(set(contratos)))
    
    def test_contratos_activos_excluye_eliminados(self):
        """contratos_activos() excluye lotes eliminados"""
        # Soft delete del único lote con CONT-2024-001
        self.lote_con_contrato.soft_delete()
        
        contratos = Lote.contratos_activos()
        self.assertNotIn('CONT-2024-001', contratos)
    
    def test_indice_numero_contrato(self):
        """Verificar que existe índice en numero_contrato para performance"""
        from django.db import connection
        
        # Verificar que el campo tiene db_index=True
        self.assertTrue(
            Lote._meta.get_field('numero_contrato').db_index or
            any('contrato' in idx.name for idx in Lote._meta.indexes)
        )


class ISS008010IntegracionTest(BaseTestCase):
    """Tests de integración entre ISS-008 y ISS-010"""
    
    def setUp(self):
        """Crear escenario completo"""
        # Lote con contrato
        self.lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOT-INT-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible',
            numero_contrato='CONT-INTEG-001'
        )
    
    def test_stock_comprometido_no_afecta_contrato(self):
        """El stock comprometido es independiente del contrato"""
        # Crear requisición que compromete stock
        req = Requisicion.objects.create(
            folio='REQ-INT-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=30,
            cantidad_autorizada=25
        )
        
        # El resumen del contrato muestra cantidad actual (no afectada por comprometido)
        resumen_contrato = Lote.resumen_por_contrato('CONT-INTEG-001')
        self.assertEqual(resumen_contrato['total_cantidad_actual'], 100)
        
        # Pero el stock disponible real sí descuenta comprometido
        stock_disponible = self.producto.get_stock_disponible_real()
        self.assertEqual(stock_disponible, 75)  # 100 - 25 comprometidos
    
    def test_trazabilidad_completa_lote_contrato_requisicion(self):
        """Trazabilidad: Contrato -> Lote -> Requisición"""
        req = Requisicion.objects.create(
            folio='REQ-TRAZ-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        detalle = DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            lote=self.lote,
            cantidad_solicitada=10,
            cantidad_autorizada=10
        )
        
        # Desde detalle -> lote -> contrato
        self.assertEqual(detalle.lote.numero_contrato, 'CONT-INTEG-001')
        
        # Desde contrato -> lotes -> detalles
        lotes_contrato = Lote.por_contrato('CONT-INTEG-001')
        detalles = DetalleRequisicion.objects.filter(lote__in=lotes_contrato)
        self.assertEqual(detalles.count(), 1)
        self.assertEqual(detalles.first().requisicion.folio, 'REQ-TRAZ-001')
