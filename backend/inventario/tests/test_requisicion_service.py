"""
Tests para el servicio transaccional de requisiciones.

ISS-011: Transacciones atómicas en surtido
ISS-021: Servicio transaccional con rollback
ISS-014: Bloqueo optimista de lotes
ISS-030: Control de acceso por centro
"""
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock
import threading

from core.models import Centro, Producto, Lote, Requisicion, DetalleRequisicion, Movimiento
from inventario.services import (
    RequisicionService,
    StockInsuficienteError,
    EstadoInvalidoError,
    PermisoRequisicionError,
    CentroPermissionMixin,
)

User = get_user_model()


def is_farmacia_or_admin_mock(user):
    """Mock de función is_farmacia_or_admin"""
    rol = getattr(user, 'rol', '')
    return rol in ['admin', 'farmacia'] or user.is_superuser


def get_user_centro_mock(user):
    """Mock de función get_user_centro"""
    return getattr(user, 'centro', None)


class RequisicionServiceAtomicityTests(TransactionTestCase):
    """
    ISS-011: Tests para verificar atomicidad de transacciones en surtido.
    Usa TransactionTestCase para permitir rollback real.
    """
    
    def setUp(self):
        """Configurar datos de prueba"""
        self.admin = User.objects.create_superuser(
            username='admin_atomic',
            email='admin@atomic.test',
            password='Admin@123',
            rol='admin'
        )
        
        self.centro = Centro.objects.create(
            clave='CENT-ATOM',
            nombre='Centro Atomicidad',
            direccion='Dirección de prueba',
            telefono='555-0000',
            activo=True
        )
        
        self.usuario_centro = User.objects.create_user(
            username='user_centro',
            email='centro@test.com',
            password='User@123',
            rol='centro',
            centro=self.centro
        )
        
        self.producto = Producto.objects.create(
            clave='PROD-ATOM-001',
            descripcion='Producto para pruebas atómicas',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=50,
            activo=True
        )
        
        # Lote en farmacia central (centro=None)
        self.lote_farmacia = Lote.objects.create(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOTE-ATOM-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Crear requisición autorizada
        self.requisicion = Requisicion.objects.create(
            folio='REQ-ATOM-001',
            centro=self.centro,
            usuario_solicita=self.usuario_centro,
            estado='autorizada'
        )
        
        self.detalle = DetalleRequisicion.objects.create(
            requisicion=self.requisicion,
            producto=self.producto,
            cantidad_solicitada=50,
            cantidad_autorizada=50,
            cantidad_surtida=0
        )
    
    def test_surtir_exitoso_descuenta_stock(self):
        """ISS-011: Surtido exitoso debe descontar stock correctamente"""
        service = RequisicionService(self.requisicion, self.admin)
        
        resultado = service.surtir(
            is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
            get_user_centro_fn=get_user_centro_mock
        )
        
        self.assertTrue(resultado['exito'])
        
        # Verificar stock descontado de farmacia
        self.lote_farmacia.refresh_from_db()
        self.assertEqual(self.lote_farmacia.cantidad_actual, 50)
        
        # Verificar lote creado en centro
        lote_centro = Lote.objects.filter(
            producto=self.producto,
            centro=self.centro,
            numero_lote='LOTE-ATOM-001'
        ).first()
        self.assertIsNotNone(lote_centro)
        self.assertEqual(lote_centro.cantidad_actual, 50)
        
        # Verificar requisición actualizada
        self.requisicion.refresh_from_db()
        self.assertEqual(self.requisicion.estado, 'surtida')
    
    def test_surtir_crea_movimientos(self):
        """ISS-011: Surtido debe crear movimientos de entrada y salida"""
        movimientos_antes = Movimiento.objects.count()
        
        service = RequisicionService(self.requisicion, self.admin)
        service.surtir(
            is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
            get_user_centro_fn=get_user_centro_mock
        )
        
        movimientos_despues = Movimiento.objects.count()
        # Debe crear al menos 2 movimientos: salida de farmacia + entrada a centro
        self.assertGreaterEqual(movimientos_despues - movimientos_antes, 2)
        
        # Verificar movimiento de salida
        mov_salida = Movimiento.objects.filter(
            lote=self.lote_farmacia,
            tipo='salida'
        ).first()
        self.assertIsNotNone(mov_salida)
        self.assertEqual(mov_salida.cantidad, -50)
        
        # Verificar movimiento de entrada
        lote_centro = Lote.objects.filter(centro=self.centro, producto=self.producto).first()
        mov_entrada = Movimiento.objects.filter(
            lote=lote_centro,
            tipo='entrada'
        ).first()
        self.assertIsNotNone(mov_entrada)
        self.assertEqual(mov_entrada.cantidad, 50)
    
    def test_surtir_estado_invalido_no_permite(self):
        """ISS-011: No debe surtir requisición en estado inválido"""
        self.requisicion.estado = 'borrador'
        self.requisicion.save()
        
        service = RequisicionService(self.requisicion, self.admin)
        
        with self.assertRaises(EstadoInvalidoError) as ctx:
            service.surtir(
                is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
                get_user_centro_fn=get_user_centro_mock
            )
        
        self.assertEqual(ctx.exception.code, 'estado_invalido')
        
        # Stock no debe haberse afectado
        self.lote_farmacia.refresh_from_db()
        self.assertEqual(self.lote_farmacia.cantidad_actual, 100)
    
    def test_surtir_stock_insuficiente_rollback(self):
        """ISS-011: Sin stock suficiente debe hacer rollback completo"""
        # Reducir stock a menos de lo solicitado
        self.lote_farmacia.cantidad_actual = 10
        self.lote_farmacia.save()
        
        service = RequisicionService(self.requisicion, self.admin)
        
        with self.assertRaises(StockInsuficienteError):
            service.surtir(
                is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
                get_user_centro_fn=get_user_centro_mock
            )
        
        # Verificar que no se creó lote en centro
        lote_centro = Lote.objects.filter(
            producto=self.producto,
            centro=self.centro
        ).first()
        self.assertIsNone(lote_centro)
        
        # Stock original intacto
        self.lote_farmacia.refresh_from_db()
        self.assertEqual(self.lote_farmacia.cantidad_actual, 10)


class RequisicionServicePermissionTests(TestCase):
    """
    ISS-030: Tests para control de acceso por centro.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_perm',
            email='admin@perm.test',
            password='Admin@123',
            rol='admin'
        )
        
        cls.centro_a = Centro.objects.create(
            clave='CENT-A',
            nombre='Centro A',
            direccion='Dir A',
            telefono='555-0001',
            activo=True
        )
        
        cls.centro_b = Centro.objects.create(
            clave='CENT-B',
            nombre='Centro B',
            direccion='Dir B',
            telefono='555-0002',
            activo=True
        )
        
        cls.usuario_centro_a = User.objects.create_user(
            username='user_a',
            email='user_a@test.com',
            password='User@123',
            rol='centro',
            centro=cls.centro_a
        )
        
        cls.usuario_centro_b = User.objects.create_user(
            username='user_b',
            email='user_b@test.com',
            password='User@123',
            rol='centro',
            centro=cls.centro_b
        )
        
        cls.usuario_farmacia = User.objects.create_user(
            username='user_farm',
            email='farm@test.com',
            password='User@123',
            rol='farmacia'
        )
        
        cls.producto = Producto.objects.create(
            clave='PROD-PERM-001',
            descripcion='Producto permisos',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('5.00'),
            stock_minimo=10,
            activo=True
        )
        
        cls.lote_farmacia = Lote.objects.create(
            producto=cls.producto,
            centro=None,
            numero_lote='LOTE-PERM-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
    
    def test_usuario_centro_no_puede_surtir(self):
        """ISS-003: Solo farmacia/admin pueden surtir - centros NO pueden"""
        requisicion = Requisicion.objects.create(
            folio='REQ-PERM-001',
            centro=self.centro_a,
            usuario_solicita=self.usuario_centro_a,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=self.producto,
            cantidad_solicitada=10,
            cantidad_autorizada=10
        )
        
        service = RequisicionService(requisicion, self.usuario_centro_a)
        
        # Usuario de centro NO puede surtir (ISS-003)
        with self.assertRaises(PermisoRequisicionError) as ctx:
            service.surtir(
                is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
                get_user_centro_fn=get_user_centro_mock
            )
        
        self.assertIn('farmacia central', str(ctx.exception))
    
    def test_usuario_centro_no_puede_surtir_otro_centro(self):
        """ISS-030: Usuario de centro NO puede surtir requisiciones de otro centro"""
        requisicion = Requisicion.objects.create(
            folio='REQ-PERM-002',
            centro=self.centro_b,  # Centro B
            usuario_solicita=self.usuario_centro_b,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=self.producto,
            cantidad_solicitada=10,
            cantidad_autorizada=10
        )
        
        # Usuario de Centro A intenta surtir requisición de Centro B
        service = RequisicionService(requisicion, self.usuario_centro_a)
        
        with self.assertRaises(PermisoRequisicionError):
            service.surtir(
                is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
                get_user_centro_fn=get_user_centro_mock
            )
    
    def test_usuario_farmacia_puede_surtir_cualquier_centro(self):
        """ISS-030: Usuario de farmacia puede surtir cualquier centro"""
        requisicion = Requisicion.objects.create(
            folio='REQ-PERM-003',
            centro=self.centro_b,
            usuario_solicita=self.usuario_centro_b,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=self.producto,
            cantidad_solicitada=10,
            cantidad_autorizada=10
        )
        
        service = RequisicionService(requisicion, self.usuario_farmacia)
        
        resultado = service.surtir(
            is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
            get_user_centro_fn=get_user_centro_mock
        )
        
        self.assertTrue(resultado['exito'])
    
    def test_superuser_puede_surtir_cualquier_centro(self):
        """ISS-030: Superusuario puede surtir cualquier centro"""
        requisicion = Requisicion.objects.create(
            folio='REQ-PERM-004',
            centro=self.centro_a,
            usuario_solicita=self.usuario_centro_a,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=requisicion,
            producto=self.producto,
            cantidad_solicitada=10,
            cantidad_autorizada=10
        )
        
        service = RequisicionService(requisicion, self.admin)
        
        resultado = service.surtir(
            is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
            get_user_centro_fn=get_user_centro_mock
        )
        
        self.assertTrue(resultado['exito'])


class LoteLockingTests(TransactionTestCase):
    """
    ISS-014: Tests para bloqueo optimista de lotes.
    """
    
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin_lock',
            email='admin@lock.test',
            password='Admin@123',
            rol='admin'
        )
        
        self.centro = Centro.objects.create(
            clave='CENT-LOCK',
            nombre='Centro Lock',
            direccion='Dir',
            telefono='555-0003',
            activo=True
        )
        
        self.producto = Producto.objects.create(
            clave='PROD-LOCK-001',
            descripcion='Producto lock test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10,
            activo=True
        )
        
        self.lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOTE-LOCK-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
    
    def test_descuento_atomico_no_genera_stock_negativo(self):
        """
        ISS-014: Descuentos atómicos deben prevenir stock negativo.
        
        Nota ISS-004: Ahora se considera el stock comprometido por otras requisiciones
        autorizadas. Si req2 está autorizada y compromete stock, req1 no podrá
        usar ese stock.
        """
        # Crear un segundo centro para que las requisiciones no compartan stock
        centro2 = Centro.objects.create(
            clave='CENT-LOCK-2',
            nombre='Centro Lock 2',
            direccion='Dir2',
            telefono='555-0099',
            activo=True
        )
        
        # Crear primera requisición ANTES de la segunda
        # Esto asegura que cuando la primera se surte, no hay stock comprometido
        req1 = Requisicion.objects.create(
            folio='REQ-LOCK-001',
            centro=self.centro,  # Centro 1
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req1,
            producto=self.producto,
            cantidad_solicitada=70,
            cantidad_autorizada=70
        )
        
        # Primera requisición debería funcionar (70 de 100, sin stock comprometido)
        service1 = RequisicionService(req1, self.admin)
        resultado1 = service1.surtir(
            is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
            get_user_centro_fn=get_user_centro_mock
        )
        self.assertTrue(resultado1['exito'])
        
        # Verificar stock central después de primera req: 100 - 70 = 30
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, 30)
        
        # Ahora crear segunda requisición que pide 70 (más que el stock restante)
        req2 = Requisicion.objects.create(
            folio='REQ-LOCK-002',
            centro=centro2,  # Centro 2 diferente
            usuario_solicita=self.admin,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req2,
            producto=self.producto,
            cantidad_solicitada=70,
            cantidad_autorizada=70
        )
        
        # Segunda debe fallar por stock insuficiente (pide 70, solo hay 30 centrales)
        service2 = RequisicionService(req2, self.admin)
        with self.assertRaises(StockInsuficienteError):
            service2.surtir(
                is_farmacia_or_admin_fn=is_farmacia_or_admin_mock,
                get_user_centro_fn=get_user_centro_mock
            )
        
        # Verificar que el lote nunca quedó negativo
        self.lote.refresh_from_db()
        self.assertGreaterEqual(self.lote.cantidad_actual, 0)


class TransicionEstadoTests(TestCase):
    """
    ISS-012: Tests para validación de transiciones de estado.
    """
    
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username='admin_trans',
            email='admin@trans.test',
            password='Admin@123'
        )
        
        cls.centro = Centro.objects.create(
            clave='CENT-TRANS',
            nombre='Centro Transiciones',
            direccion='Dir',
            telefono='555-0004',
            activo=True
        )
    
    def test_transicion_borrador_a_enviada_valida(self):
        """Transición borrador → enviada es válida"""
        req = Requisicion.objects.create(
            folio='REQ-TRANS-001',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='borrador'
        )
        
        self.assertTrue(req.puede_transicionar_a('enviada'))
    
    def test_transicion_borrador_a_surtida_invalida(self):
        """Transición borrador → surtida es inválida"""
        req = Requisicion.objects.create(
            folio='REQ-TRANS-002',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='borrador'
        )
        
        self.assertFalse(req.puede_transicionar_a('surtida'))
    
    def test_transiciones_disponibles(self):
        """Verificar transiciones disponibles desde cada estado"""
        req = Requisicion.objects.create(
            folio='REQ-TRANS-003',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='borrador'
        )
        
        self.assertEqual(
            set(req.get_transiciones_disponibles()),
            {'enviada', 'cancelada'}
        )
        
        req.estado = 'surtida'
        self.assertEqual(
            set(req.get_transiciones_disponibles()),
            {'recibida'}
        )
        
        req.estado = 'cancelada'
        self.assertEqual(req.get_transiciones_disponibles(), [])
    
    def test_estado_terminal(self):
        """Estados terminales no tienen transiciones"""
        req = Requisicion.objects.create(
            folio='REQ-TRANS-004',
            centro=self.centro,
            usuario_solicita=self.admin,
            estado='cancelada'
        )
        
        self.assertTrue(req.es_estado_terminal())
        
        req.estado = 'recibida'
        self.assertTrue(req.es_estado_terminal())
        
        req.estado = 'autorizada'
        self.assertFalse(req.es_estado_terminal())
