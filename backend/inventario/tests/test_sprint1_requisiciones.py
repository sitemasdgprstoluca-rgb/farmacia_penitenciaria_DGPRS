"""
ISS-027: Suite completa de tests para requisiciones.

Tests para:
- ISS-012: Máquina de estados
- ISS-020: Validación de stock al crear requisición
- ISS-024: Validación de inventario por centro
- ISS-026: Reconciliación de inventario
"""
import logging
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.db import transaction

from core.models import (
    Centro, Producto, Lote, Requisicion, DetalleRequisicion, Movimiento
)
from inventario.services import (
    # State Machine
    EstadoRequisicion,
    RequisicionStateMachine,
    TransicionInvalidaError,
    PrecondicionFallidaError,
    # Validation
    StockValidationService,
    StockValidationError,
    CentroInventoryValidator,
    # Reconciliation
    InventoryReconciliationService,
    validar_stock_para_requisicion,
    reconciliar_inventario,
)

User = get_user_model()
logger = logging.getLogger(__name__)


# =============================================================================
# ISS-012: Tests de Máquina de Estados
# =============================================================================

class StateMachineBasicTests(TestCase):
    """Tests básicos de la máquina de estados."""
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_sm',
            email='admin@sm.test',
            password='Admin@123'
        )
        cls.centro = Centro.objects.create(
            clave='CTR-SM',
            nombre='Centro State Machine',
            direccion='Dir',
            telefono='555-0001',
            activo=True
        )
        cls.producto = Producto.objects.create(
            clave='PROD-SM-001',
            descripcion='Producto State Machine Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
        cls.lote = Lote.objects.create(
            producto=cls.producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-SM-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
    
    def _crear_requisicion(self, estado='borrador', con_detalle=True):
        """Helper para crear requisición."""
        req = Requisicion.objects.create(
            folio=f'REQ-SM-{Requisicion.objects.count() + 1:03d}',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado=estado
        )
        if con_detalle:
            DetalleRequisicion.objects.create(
                requisicion=req,
                producto=self.producto,
                cantidad_solicitada=10
            )
        return req
    
    def test_estado_inicial_borrador(self):
        """ISS-012: Estado inicial debe ser borrador."""
        req = self._crear_requisicion()
        sm = RequisicionStateMachine(req)
        
        self.assertEqual(sm.estado_actual, EstadoRequisicion.BORRADOR)
    
    def test_transiciones_validas_desde_borrador(self):
        """ISS-012: Desde borrador solo se puede ir a enviada o cancelada."""
        req = self._crear_requisicion()
        sm = RequisicionStateMachine(req)
        
        transiciones = sm.get_transiciones_disponibles()
        
        self.assertIn('enviada', transiciones)
        self.assertIn('cancelada', transiciones)
        self.assertEqual(len(transiciones), 2)
    
    def test_transicion_borrador_a_enviada(self):
        """ISS-012: Transición válida borrador -> enviada."""
        req = self._crear_requisicion()
        sm = RequisicionStateMachine(req)
        
        self.assertTrue(sm.puede_transicionar_a('enviada'))
        
        resultado = sm.transicionar('enviada', usuario=self.admin)
        
        self.assertTrue(resultado)
        self.assertEqual(req.estado, 'enviada')
    
    def test_transicion_invalida_borrador_a_surtida(self):
        """ISS-012: Transición inválida debe fallar."""
        req = self._crear_requisicion()
        sm = RequisicionStateMachine(req)
        
        self.assertFalse(sm.puede_transicionar_a('surtida'))
        
        with self.assertRaises(PrecondicionFallidaError):
            sm.transicionar('surtida', usuario=self.admin)
    
    def test_enviar_sin_detalles_falla(self):
        """ISS-012: No se puede enviar requisición sin detalles."""
        req = self._crear_requisicion(con_detalle=False)
        sm = RequisicionStateMachine(req)
        
        errores = sm.validar_transicion('enviada')
        
        self.assertTrue(len(errores) > 0)
        self.assertTrue(any('producto' in e.lower() for e in errores))
    
    def test_rechazar_requiere_motivo(self):
        """ISS-012: Rechazar requiere motivo."""
        req = self._crear_requisicion(estado='enviada')
        sm = RequisicionStateMachine(req)
        
        errores = sm.validar_transicion('rechazada')
        
        self.assertTrue(any('motivo' in e.lower() for e in errores))
        
        # Con motivo debe funcionar
        errores = sm.validar_transicion('rechazada', motivo='Stock agotado')
        self.assertEqual(len(errores), 0)
    
    def test_estado_terminal_no_permite_transiciones(self):
        """ISS-012: Estados terminales no permiten más transiciones."""
        req = self._crear_requisicion(estado='recibida')
        sm = RequisicionStateMachine(req)
        
        self.assertTrue(sm.es_estado_terminal())
        self.assertEqual(len(sm.get_transiciones_disponibles()), 0)
    
    def test_flujo_completo_requisicion(self):
        """ISS-012: Flujo completo borrador -> enviada -> autorizada -> surtida -> recibida."""
        req = self._crear_requisicion()
        sm = RequisicionStateMachine(req)
        
        # Borrador -> Enviada
        sm.transicionar('enviada', usuario=self.admin)
        self.assertEqual(req.estado, 'enviada')
        
        # Enviada -> Autorizada (asignar cantidad autorizada primero)
        for detalle in req.detalles.all():
            detalle.cantidad_autorizada = detalle.cantidad_solicitada
            detalle.save()
        
        sm.transicionar('autorizada', usuario=self.admin)
        self.assertEqual(req.estado, 'autorizada')
        self.assertIsNotNone(req.fecha_autorizacion)
        
        # Autorizada -> Surtida (simular surtido)
        for detalle in req.detalles.all():
            detalle.cantidad_surtida = detalle.cantidad_autorizada
            detalle.save()
        
        sm.transicionar('surtida', usuario=self.admin, validar_precondiciones=False)
        self.assertEqual(req.estado, 'surtida')
        
        # Surtida -> Recibida
        sm.transicionar('recibida', usuario=self.admin, observaciones='Recibido conforme')
        self.assertEqual(req.estado, 'recibida')
        self.assertIsNotNone(req.fecha_recibido)


class StateMachineEdgeCasesTests(TestCase):
    """Tests de casos límite de la máquina de estados."""
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_edge',
            email='admin@edge.test',
            password='Admin@123'
        )
        cls.centro = Centro.objects.create(
            clave='CTR-EDGE',
            nombre='Centro Edge Cases',
            direccion='Dir',
            telefono='555-0002',
            activo=True
        )
        cls.producto = Producto.objects.create(
            clave='PROD-EDGE-001',
            descripcion='Producto Edge Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=5,
            activo=True
        )
    
    def test_producto_inactivo_bloquea_envio(self):
        """ISS-012: No se puede enviar requisición con producto inactivo."""
        # Crear producto inactivo
        producto_inactivo = Producto.objects.create(
            clave='PROD-INACT',
            descripcion='Producto Inactivo',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('5.00'),
            stock_minimo=1,
            activo=False
        )
        
        req = Requisicion.objects.create(
            folio='REQ-EDGE-001',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='borrador'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=producto_inactivo,
            cantidad_solicitada=5
        )
        
        sm = RequisicionStateMachine(req)
        errores = sm.validar_transicion('enviada')
        
        self.assertTrue(any('inactivo' in e.lower() for e in errores))
    
    def test_cantidad_cero_bloquea_envio(self):
        """
        ISS-012: Cantidad <= 0 bloquea envío.
        ISS-019: Ahora hay un CHECK constraint que previene cantidad_solicitada <= 0
        """
        from django.db.utils import IntegrityError
        
        req = Requisicion.objects.create(
            folio='REQ-EDGE-002',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='borrador'
        )
        
        # El constraint de BD previene crear detalles con cantidad_solicitada <= 0
        with self.assertRaises(IntegrityError):
            DetalleRequisicion.objects.create(
                requisicion=req,
                producto=self.producto,
                cantidad_solicitada=0  # Cantidad inválida - debe fallar por constraint
            )


# =============================================================================
# ISS-020: Tests de Validación de Stock
# =============================================================================

class StockValidationTests(TestCase):
    """Tests de validación de stock."""
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_stock',
            email='admin@stock.test',
            password='Admin@123'
        )
        cls.centro = Centro.objects.create(
            clave='CTR-STOCK',
            nombre='Centro Stock Test',
            direccion='Dir',
            telefono='555-0003',
            activo=True
        )
        cls.producto = Producto.objects.create(
            clave='PROD-STOCK-001',
            descripcion='Producto Stock Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
        cls.lote = Lote.objects.create(
            producto=cls.producto,
            centro=None,
            numero_lote='LOTE-STOCK-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible'
        )
    
    def test_validar_stock_suficiente(self):
        """ISS-020: Stock suficiente debe validar OK."""
        validator = StockValidationService()
        
        resultado = validator.validar_stock_producto(self.producto, 30)
        
        self.assertTrue(resultado.is_valid)
        self.assertEqual(resultado.deficit, 0)
    
    def test_validar_stock_insuficiente(self):
        """ISS-020: Stock insuficiente debe fallar."""
        validator = StockValidationService()
        
        resultado = validator.validar_stock_producto(self.producto, 100)
        
        self.assertFalse(resultado.is_valid)
        self.assertEqual(resultado.deficit, 50)  # 100 - 50 disponible
        self.assertIn('insuficiente', resultado.mensaje.lower())
    
    def test_validar_requisicion_completa(self):
        """ISS-020: Validar todos los items de una requisición."""
        # Crear producto sin stock
        producto_sin_stock = Producto.objects.create(
            clave='PROD-SIN-STOCK',
            descripcion='Sin Stock',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('5.00'),
            stock_minimo=1,
            activo=True
        )
        
        req = Requisicion.objects.create(
            folio='REQ-STOCK-001',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        
        # Item con stock OK
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=10,
            cantidad_autorizada=10
        )
        
        # Item sin stock
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=producto_sin_stock,
            cantidad_solicitada=5,
            cantidad_autorizada=5
        )
        
        errores = validar_stock_para_requisicion(req, solo_autorizados=True)
        
        self.assertEqual(len(errores), 1)
        self.assertEqual(errores[0]['producto'], 'PROD-SIN-STOCK')
    
    def test_validar_stock_considera_centro(self):
        """ISS-020: Validación considera stock del centro destino."""
        # Crear lote en el centro (mismo numero_lote y fecha que origen)
        lote_centro = Lote.objects.create(
            producto=self.producto,
            centro=self.centro,
            numero_lote=self.lote.numero_lote,  # Debe coincidir con origen
            fecha_caducidad=self.lote.fecha_caducidad,  # Debe coincidir con origen
            cantidad_inicial=30,
            cantidad_actual=30,
            estado='disponible',
            lote_origen=self.lote
        )
        
        validator = StockValidationService(centro=self.centro)
        
        # Ahora tenemos 50 (central) + 30 (centro) = 80
        resultado = validator.validar_stock_producto(self.producto, 70)
        
        self.assertTrue(resultado.is_valid)
    
    def test_validar_excluye_lotes_eliminados(self):
        """ISS-020: No cuenta lotes con soft delete."""
        from django.utils import timezone
        
        # Soft delete del lote
        self.lote.deleted_at = timezone.now()
        self.lote.save()
        
        validator = StockValidationService()
        resultado = validator.validar_stock_producto(self.producto, 10)
        
        self.assertFalse(resultado.is_valid)
        self.assertEqual(resultado.cantidad_disponible, 0)
        
        # Restaurar
        self.lote.deleted_at = None
        self.lote.save()


# =============================================================================
# ISS-024: Tests de Validación por Centro
# =============================================================================

class CentroInventoryValidationTests(TestCase):
    """Tests de validación de inventario por centro."""
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_centro',
            email='admin@centro.test',
            password='Admin@123'
        )
        cls.centro_a = Centro.objects.create(
            clave='CTR-A',
            nombre='Centro A',
            direccion='Dir A',
            telefono='555-0010',
            activo=True
        )
        cls.centro_b = Centro.objects.create(
            clave='CTR-B',
            nombre='Centro B',
            direccion='Dir B',
            telefono='555-0011',
            activo=True
        )
        cls.usuario_centro_a = User.objects.create_user(
            username='user_centro_a',
            email='user_a@centro.test',
            password='User@123',
            rol='centro'
        )
        cls.usuario_centro_a.centro = cls.centro_a
        cls.usuario_centro_a.save()
        
        cls.usuario_farmacia = User.objects.create_user(
            username='user_farmacia',
            email='user_f@centro.test',
            password='User@123',
            rol='farmacia'
        )
        
        cls.producto = Producto.objects.create(
            clave='PROD-CENT-001',
            descripcion='Producto Centros Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=5,
            activo=True
        )
        
        # Lote en farmacia central
        cls.lote_central = Lote.objects.create(
            producto=cls.producto,
            centro=None,
            numero_lote='LOTE-CENTRAL',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Lote en Centro A (mismo numero_lote y fecha que origen para trazabilidad)
        cls.lote_centro_a = Lote.objects.create(
            producto=cls.producto,
            centro=cls.centro_a,
            numero_lote=cls.lote_central.numero_lote,  # Debe coincidir
            fecha_caducidad=cls.lote_central.fecha_caducidad,  # Debe coincidir
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible',
            lote_origen=cls.lote_central
        )
    
    def test_admin_accede_a_todos_los_lotes(self):
        """ISS-024: Admin puede acceder a cualquier lote."""
        validator = CentroInventoryValidator(self.admin)
        
        # Acceso a lote central
        valido, error = validator.validar_acceso_lote(self.lote_central)
        self.assertTrue(valido)
        
        # Acceso a lote de centro
        valido, error = validator.validar_acceso_lote(self.lote_centro_a)
        self.assertTrue(valido)
    
    def test_farmacia_accede_a_todos_los_lotes(self):
        """ISS-024: Usuario farmacia puede acceder a cualquier lote."""
        validator = CentroInventoryValidator(self.usuario_farmacia)
        
        valido, error = validator.validar_acceso_lote(self.lote_central)
        self.assertTrue(valido)
        
        valido, error = validator.validar_acceso_lote(self.lote_centro_a)
        self.assertTrue(valido)
    
    def test_usuario_centro_solo_accede_a_su_centro(self):
        """ISS-024: Usuario de centro solo accede a lotes de su centro."""
        validator = CentroInventoryValidator(self.usuario_centro_a)
        
        # Su propio centro - OK
        valido, error = validator.validar_acceso_lote(self.lote_centro_a)
        self.assertTrue(valido)
        
        # Farmacia central - NO
        valido, error = validator.validar_acceso_lote(self.lote_central)
        self.assertFalse(valido)
        self.assertIn('farmacia central', error.lower())
    
    def test_usuario_centro_no_accede_a_otro_centro(self):
        """ISS-024: Usuario de centro A no accede a lotes de centro B."""
        # Crear lote en centro B (mismo numero_lote y fecha que origen)
        lote_centro_b = Lote.objects.create(
            producto=self.producto,
            centro=self.centro_b,
            numero_lote=self.lote_central.numero_lote,  # Debe coincidir
            fecha_caducidad=self.lote_central.fecha_caducidad,  # Debe coincidir
            cantidad_inicial=30,
            cantidad_actual=30,
            estado='disponible',
            lote_origen=self.lote_central
        )
        
        validator = CentroInventoryValidator(self.usuario_centro_a)
        
        valido, error = validator.validar_acceso_lote(lote_centro_b)
        self.assertFalse(valido)
        self.assertIn('Centro B', error)
    
    def test_validar_salida_stock_suficiente(self):
        """ISS-024: Validar salida con stock suficiente."""
        validator = CentroInventoryValidator(self.usuario_centro_a)
        
        valido, error = validator.validar_salida_lote(self.lote_centro_a, 20)
        self.assertTrue(valido)
    
    def test_validar_salida_stock_insuficiente(self):
        """ISS-024: Validar salida con stock insuficiente."""
        validator = CentroInventoryValidator(self.usuario_centro_a)
        
        valido, error = validator.validar_salida_lote(self.lote_centro_a, 100)
        self.assertFalse(valido)
        self.assertIn('insuficiente', error.lower())
    
    def test_get_lotes_disponibles_usuario_centro(self):
        """ISS-024: Usuario centro solo ve sus lotes."""
        validator = CentroInventoryValidator(self.usuario_centro_a)
        
        lotes = validator.get_lotes_disponibles_usuario(self.producto)
        
        self.assertEqual(lotes.count(), 1)
        self.assertEqual(lotes.first().pk, self.lote_centro_a.pk)
    
    def test_get_lotes_disponibles_admin(self):
        """ISS-024: Admin ve todos los lotes."""
        validator = CentroInventoryValidator(self.admin)
        
        lotes = validator.get_lotes_disponibles_usuario(self.producto)
        
        self.assertGreaterEqual(lotes.count(), 2)


# =============================================================================
# ISS-026: Tests de Reconciliación
# =============================================================================

class ReconciliationTests(TestCase):
    """Tests de reconciliación de inventario."""
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_recon',
            email='admin@recon.test',
            password='Admin@123'
        )
        cls.centro = Centro.objects.create(
            clave='CTR-RECON',
            nombre='Centro Reconciliacion',
            direccion='Dir',
            telefono='555-0020',
            activo=True
        )
        cls.producto = Producto.objects.create(
            clave='PROD-RECON-001',
            descripcion='Producto Reconciliacion Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
    
    def test_reconciliar_lote_sin_movimientos(self):
        """ISS-026: Lote nuevo sin movimientos debe estar OK."""
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-RECON-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        service = InventoryReconciliationService()
        resultado = service.reconciliar_lote(lote)
        
        self.assertEqual(resultado.estado, 'ok')
        self.assertEqual(resultado.diferencia, 0)
    
    def test_reconciliar_lote_con_movimientos_correctos(self):
        """ISS-026: Lote con movimientos correctos debe estar OK."""
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-RECON-002',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=80,  # Salieron 20
            estado='disponible'
        )
        
        # Crear movimiento de salida
        mov = Movimiento.objects.create(
            tipo='salida',
            lote=lote,
            cantidad=-20,
            usuario=self.admin,
            observaciones='Surtido test'
        )
        
        service = InventoryReconciliationService()
        resultado = service.reconciliar_lote(lote)
        
        self.assertEqual(resultado.estado, 'ok')
        self.assertEqual(resultado.diferencia, 0)
    
    def test_reconciliar_detecta_discrepancia(self):
        """ISS-026: Detectar discrepancia en stock."""
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-RECON-003',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=70,  # Dice 70
            estado='disponible'
        )
        
        # Pero solo salieron 20 según movimientos
        Movimiento.objects.create(
            tipo='salida',
            lote=lote,
            cantidad=-20,
            usuario=self.admin,
            observaciones='Surtido test'
        )
        
        # Stock esperado = 100 - 20 = 80, pero sistema dice 70
        service = InventoryReconciliationService()
        resultado = service.reconciliar_lote(lote)
        
        self.assertIn(resultado.estado, ['discrepancia', 'critico'])
        self.assertEqual(resultado.diferencia, -10)  # 70 - 80 = -10
    
    def test_reconciliar_global(self):
        """ISS-026: Reconciliación global del sistema."""
        # Crear algunos lotes
        for i in range(3):
            Lote.objects.create(
                producto=self.producto,
                centro=None,
                numero_lote=f'LOTE-GLOB-{i:03d}',
                fecha_caducidad=date.today() + timedelta(days=365),
                cantidad_inicial=50,
                cantidad_actual=50,
                estado='disponible'
            )
        
        resultado = reconciliar_inventario(global_=True, solo_discrepancias=False)
        
        self.assertIn('resumen', resultado)
        self.assertIn('detalles', resultado)
        self.assertGreater(resultado['resumen']['total_lotes'], 0)
    
    def test_corregir_discrepancia(self):
        """ISS-026: Corregir discrepancia de stock."""
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-CORREC-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=70,  # Incorrecto
            estado='disponible'
        )
        
        service = InventoryReconciliationService()
        resultado = service.corregir_discrepancia(
            lote=lote,
            nuevo_stock=80,  # Correcto
            motivo='Ajuste físico',
            usuario=self.admin
        )
        
        self.assertTrue(resultado)
        
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, 80)
        
        # Verificar movimiento de ajuste creado
        ajuste = Movimiento.objects.filter(
            lote=lote,
            tipo='ajuste'
        ).first()
        self.assertIsNotNone(ajuste)
        self.assertEqual(ajuste.cantidad, 10)  # 80 - 70


# =============================================================================
# Tests de Integración
# =============================================================================

class IntegrationTests(TransactionTestCase):
    """Tests de integración de todos los servicios."""
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_integ',
            email='admin@integ.test',
            password='Admin@123'
        )
        self.centro = Centro.objects.create(
            clave='CTR-INTEG',
            nombre='Centro Integracion',
            direccion='Dir',
            telefono='555-0030',
            activo=True
        )
        self.producto = Producto.objects.create(
            clave='PROD-INTEG-001',
            descripcion='Producto Integracion Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
        self.lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-INTEG-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
    
    def test_flujo_completo_con_validaciones(self):
        """Test de flujo completo: crear req, validar stock, cambiar estados."""
        # 1. Crear requisición
        req = Requisicion.objects.create(
            folio='REQ-INTEG-001',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='borrador'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=30
        )
        
        # 2. Validar stock antes de enviar
        errores = validar_stock_para_requisicion(req)
        self.assertEqual(len(errores), 0)
        
        # 3. Cambiar a enviada usando state machine
        sm = RequisicionStateMachine(req)
        sm.transicionar('enviada', usuario=self.admin)
        
        self.assertEqual(req.estado, 'enviada')
        
        # 4. Autorizar
        for detalle in req.detalles.all():
            detalle.cantidad_autorizada = detalle.cantidad_solicitada
            detalle.save()
        
        sm.transicionar('autorizada', usuario=self.admin)
        self.assertEqual(req.estado, 'autorizada')
        
        # 5. Validar stock para surtir
        errores = validar_stock_para_requisicion(req, solo_autorizados=True)
        self.assertEqual(len(errores), 0)
    
    def test_validacion_bloquea_stock_insuficiente(self):
        """Test que validación bloquea cuando no hay stock."""
        # Crear req por más del stock disponible
        req = Requisicion.objects.create(
            folio='REQ-INTEG-002',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=200,  # Más del disponible
            cantidad_autorizada=200
        )
        
        errores = validar_stock_para_requisicion(req, solo_autorizados=True)
        
        self.assertEqual(len(errores), 1)
        self.assertEqual(errores[0]['producto'], 'PROD-INTEG-001')
        self.assertGreater(errores[0]['deficit'], 0)
