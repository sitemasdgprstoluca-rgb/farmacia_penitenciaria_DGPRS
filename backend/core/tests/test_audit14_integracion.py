"""
Tests de integración - audit14

ISS-006: Pruebas de flujo completo de requisiciones e inventario.

Cubre:
- ISS-001: Transacciones atómicas con locks en movimientos
- ISS-002: skip_validation bloqueado en producción
- ISS-003: Validación de estados en Requisicion
- ISS-005: Historial obligatorio en transiciones

Estos tests verifican escenarios críticos del flujo de negocio:
1. Ciclo completo de requisición (borrador -> surtida -> entregada)
2. Validaciones de transición de estados
3. Operaciones concurrentes de inventario (simuladas)
4. Trazabilidad de cambios de estado
"""

import logging
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase, override_settings
from django.core.exceptions import ValidationError
from django.db import transaction, connection
from django.contrib.auth import get_user_model

from core.models import (
    Centro, Producto, Lote, Movimiento, 
    Requisicion, DetalleRequisicion, RequisicionHistorialEstados
)
from core.constants import TRANSICIONES_REQUISICION, ESTADOS_TERMINALES

User = get_user_model()

logger = logging.getLogger(__name__)


class TestMovimientoTransaccionesAtomicas(TransactionTestCase):
    """
    ISS-001: Tests para verificar transacciones atómicas en movimientos.
    
    Usa TransactionTestCase para tener control real de transacciones.
    """
    
    def setUp(self):
        """Crear datos de prueba."""
        self.centro = Centro.objects.create(
            nombre='Centro Test',
            direccion='Test',
            activo=True
        )
        self.producto = Producto.objects.create(
            clave='PROD-TEST-001',
            nombre='Producto Test',
            descripcion='Producto de prueba',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            activo=True
        )
        self.lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE-TEST-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible',
            activo=True
        )
        self.usuario = User.objects.create_user(
            username='test_user',
            password='Test@123',
            email='test@test.com',
            rol='farmacia'
        )
    
    def test_aplicar_movimiento_revalida_stock(self):
        """ISS-001: Verificar que aplicar_movimiento_a_lote revalida stock."""
        # Crear movimiento de salida
        movimiento = Movimiento(
            tipo='salida',
            producto=self.producto,
            lote=self.lote,
            cantidad=50,
            usuario=self.usuario,
            motivo='Test salida'
        )
        movimiento.save()
        
        # Aplicar movimiento
        movimiento.aplicar_movimiento_a_lote()
        
        # Verificar que se descontó
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, 50)
    
    def test_aplicar_movimiento_bloquea_stock_insuficiente(self):
        """ISS-001: Verificar que se bloquea si no hay stock suficiente."""
        # Crear movimiento con más cantidad que disponible
        movimiento = Movimiento(
            tipo='salida',
            producto=self.producto,
            lote=self.lote,
            cantidad=150,  # Más que los 100 disponibles
            usuario=self.usuario,
            motivo='Test stock insuficiente'
        )
        
        # Debería fallar en clean()
        with self.assertRaises(ValidationError) as ctx:
            movimiento.full_clean()
        
        self.assertIn('cantidad', str(ctx.exception))
    
    def test_aplicar_movimiento_previene_stock_negativo(self):
        """ISS-001: Verificar que no puede quedar stock negativo."""
        # Reducir stock manualmente para simular concurrencia
        self.lote.cantidad_actual = 30
        self.lote.save(update_fields=['cantidad_actual'])
        
        # Crear movimiento que pasó validación con stock anterior
        movimiento = Movimiento(
            tipo='salida',
            producto=self.producto,
            lote=self.lote,
            cantidad=50,
            usuario=self.usuario,
            motivo='Test concurrencia'
        )
        movimiento.save(skip_validation=True)  # Simular que pasó validación antes
        
        # Al aplicar, debería detectar que ya no hay suficiente
        with self.assertRaises(ValidationError) as ctx:
            movimiento.aplicar_movimiento_a_lote(revalidar_stock=True)
        
        self.assertIn('ISS-001', str(ctx.exception))


class TestRequisicionValidacionEstados(TestCase):
    """
    ISS-003: Tests para validación de estados en Requisicion.
    """
    
    @classmethod
    def setUpTestData(cls):
        """Crear datos compartidos."""
        cls.centro = Centro.objects.create(
            nombre='Centro Requisiciones',
            direccion='Test',
            activo=True
        )
        cls.solicitante = User.objects.create_user(
            username='solicitante_test',
            password='Test@123',
            email='solicitante@test.com',
            rol='medico',
            centro=cls.centro
        )
        cls.autorizador = User.objects.create_user(
            username='autorizador_test',
            password='Test@123',
            email='autorizador@test.com',
            rol='farmacia'
        )
    
    def test_clean_valida_estado_valido(self):
        """ISS-003: clean() acepta estados válidos."""
        requisicion = Requisicion(
            numero='REQ-TEST-001',
            estado='borrador',
            centro_origen=self.centro,
            solicitante=self.solicitante
        )
        # No debería lanzar excepción
        requisicion.clean()
    
    def test_clean_rechaza_estado_invalido(self):
        """ISS-003: clean() rechaza estados inválidos."""
        requisicion = Requisicion(
            numero='REQ-TEST-002',
            estado='estado_inventado',
            centro_origen=self.centro,
            solicitante=self.solicitante
        )
        
        with self.assertRaises(ValidationError) as ctx:
            requisicion.clean()
        
        self.assertIn('estado', ctx.exception.message_dict)
    
    def test_transicion_valida_borrador_a_pendiente(self):
        """ISS-003: Transición válida de borrador a pendiente_admin."""
        requisicion = Requisicion.objects.create(
            numero='REQ-TEST-003',
            estado='borrador',
            centro_origen=self.centro,
            solicitante=self.solicitante
        )
        
        # Verificar que puede transicionar
        self.assertTrue(requisicion.puede_transicionar_a('pendiente_admin'))
        
        # Ejecutar transición
        requisicion.cambiar_estado('pendiente_admin', usuario=self.solicitante)
        requisicion.save(skip_validation=True)  # skip porque estado ya validado por cambiar_estado
        
        requisicion.refresh_from_db()
        self.assertEqual(requisicion.estado, 'pendiente_admin')
    
    def test_transicion_invalida_borrador_a_surtida(self):
        """ISS-003: No se puede pasar directamente de borrador a surtida."""
        requisicion = Requisicion.objects.create(
            numero='REQ-TEST-004',
            estado='borrador',
            centro_origen=self.centro,
            solicitante=self.solicitante
        )
        
        # Verificar que NO puede transicionar
        self.assertFalse(requisicion.puede_transicionar_a('surtida'))
        
        # Intentar cambiar estado debería fallar
        with self.assertRaises(ValidationError):
            requisicion.cambiar_estado('surtida', usuario=self.autorizador)
    
    def test_estado_terminal_no_permite_transiciones(self):
        """ISS-003: Estados terminales no permiten más transiciones."""
        requisicion = Requisicion.objects.create(
            numero='REQ-TEST-005',
            estado='entregada',
            centro_origen=self.centro,
            solicitante=self.solicitante,
            autorizador=self.autorizador,
            fecha_surtido=date.today()
        )
        
        # Verificar que es terminal
        self.assertTrue(requisicion.es_estado_terminal())
        
        # Verificar que no tiene transiciones disponibles
        transiciones = requisicion.get_transiciones_disponibles()
        self.assertEqual(len(transiciones), 0)


class TestHistorialRequisicion(TestCase):
    """
    ISS-005: Tests para historial obligatorio en transiciones.
    """
    
    @classmethod
    def setUpTestData(cls):
        """Crear datos compartidos."""
        cls.centro = Centro.objects.create(
            nombre='Centro Historial',
            direccion='Test',
            activo=True
        )
        cls.usuario = User.objects.create_user(
            username='usuario_historial',
            password='Test@123',
            email='historial@test.com',
            rol='medico',
            centro=cls.centro
        )
    
    def test_cambiar_estado_con_historial_registra_cambio(self):
        """ISS-005: cambiar_estado_con_historial registra en historial."""
        requisicion = Requisicion.objects.create(
            numero='REQ-HIST-001',
            estado='borrador',
            centro_origen=self.centro,
            solicitante=self.usuario
        )
        
        # Cambiar estado con historial
        estado_anterior = requisicion.cambiar_estado_con_historial(
            'pendiente_admin',
            usuario=self.usuario,
            motivo='Envío para revisión',
            ip_address='127.0.0.1'
        )
        requisicion.save(skip_validation=True)
        
        # Verificar que se registró en historial
        historial = RequisicionHistorialEstados.objects.filter(
            requisicion=requisicion
        ).first()
        
        self.assertIsNotNone(historial)
        self.assertEqual(historial.estado_anterior, 'borrador')
        self.assertEqual(historial.estado_nuevo, 'pendiente_admin')
        self.assertEqual(historial.usuario, self.usuario)
        self.assertEqual(historial.accion, 'enviar_admin')
    
    def test_rechazo_requiere_motivo(self):
        """ISS-005: Rechazar requisición requiere motivo."""
        requisicion = Requisicion.objects.create(
            numero='REQ-HIST-002',
            estado='en_revision',  # Estado desde el que se puede rechazar
            centro_origen=self.centro,
            solicitante=self.usuario
        )
        
        # Intentar rechazar sin motivo
        errores = requisicion.validar_transicion('rechazada', motivo=None)
        self.assertTrue(len(errores) > 0)
        self.assertIn('motivo', errores[0].lower())


class TestSkipValidationProduccion(TestCase):
    """
    ISS-002: Tests para bloqueo de skip_validation en producción.
    """
    
    @classmethod
    def setUpTestData(cls):
        """Crear datos compartidos."""
        cls.centro = Centro.objects.create(
            nombre='Centro Skip',
            direccion='Test',
            activo=True
        )
        cls.producto = Producto.objects.create(
            clave='PROD-SKIP-001',
            nombre='Producto Skip',
            descripcion='Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            activo=True
        )
        cls.lote = Lote.objects.create(
            producto=cls.producto,
            numero_lote='LOTE-SKIP-001',
            fecha_caducidad=date.today() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible',
            activo=True
        )
        cls.usuario = User.objects.create_user(
            username='skip_test',
            password='Test@123',
            email='skip@test.com',
            rol='farmacia'
        )
    
    @override_settings(DEBUG=False)
    def test_skip_validation_logea_alerta_en_produccion(self):
        """ISS-002: skip_validation loguea alerta crítica en producción."""
        with self.assertLogs('core.models', level='CRITICAL') as cm:
            movimiento = Movimiento.objects.create(
                tipo='salida',
                producto=self.producto,
                lote=self.lote,
                cantidad=10,
                usuario=self.usuario,
                motivo='Test skip producción',
                skip_validation=True
            )
        
        # Verificar que se logueó alerta
        self.assertTrue(any('ISS-002' in log for log in cm.output))
        self.assertTrue(any('PRODUCCIÓN' in log for log in cm.output))
    
    @override_settings(DEBUG=True)
    def test_skip_validation_solo_warning_en_debug(self):
        """ISS-002: skip_validation solo warning en DEBUG."""
        with self.assertLogs('core.models', level='WARNING') as cm:
            movimiento = Movimiento.objects.create(
                tipo='entrada',
                producto=self.producto,
                lote=self.lote,
                cantidad=10,
                usuario=self.usuario,
                motivo='Test skip debug',
                skip_validation=True
            )
        
        # Verificar que se logueó warning (no critical)
        self.assertTrue(any('ISS-002' in log for log in cm.output))


class TestFlujoCompletoRequisicion(TransactionTestCase):
    """
    ISS-006: Test de flujo completo de requisición.
    
    Simula el ciclo:
    borrador -> pendiente_admin -> pendiente_director -> enviada -> 
    en_revision -> autorizada -> (surtido vía servicio) -> entregada
    """
    
    def setUp(self):
        """Crear datos de prueba."""
        self.centro = Centro.objects.create(
            nombre='Centro Flujo',
            direccion='Test',
            activo=True
        )
        self.medico = User.objects.create_user(
            username='medico_flujo',
            password='Test@123',
            email='medico_flujo@test.com',
            rol='medico',
            centro=self.centro
        )
        self.admin_centro = User.objects.create_user(
            username='admin_centro_flujo',
            password='Test@123',
            email='admin_centro@test.com',
            rol='administrador_centro',
            centro=self.centro
        )
        self.director = User.objects.create_user(
            username='director_flujo',
            password='Test@123',
            email='director@test.com',
            rol='director_centro',
            centro=self.centro
        )
        self.farmacia = User.objects.create_user(
            username='farmacia_flujo',
            password='Test@123',
            email='farmacia@test.com',
            rol='farmacia'
        )
        self.producto = Producto.objects.create(
            clave='PROD-FLUJO-001',
            nombre='Producto Flujo',
            descripcion='Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            activo=True
        )
    
    def test_flujo_completo_hasta_autorizacion(self):
        """ISS-006: Flujo desde borrador hasta autorización."""
        # 1. Crear requisición en borrador
        requisicion = Requisicion.objects.create(
            numero='REQ-FLUJO-001',
            estado='borrador',
            centro_origen=self.centro,
            solicitante=self.medico
        )
        
        # 2. Enviar a administrador
        requisicion.cambiar_estado_con_historial(
            'pendiente_admin',
            usuario=self.medico,
            motivo='Solicitud de medicamentos'
        )
        requisicion.save(skip_validation=True)
        self.assertEqual(requisicion.estado, 'pendiente_admin')
        
        # 3. Administrador autoriza y envía a director
        requisicion.cambiar_estado_con_historial(
            'pendiente_director',
            usuario=self.admin_centro,
            motivo='Aprobado por administración'
        )
        requisicion.save(skip_validation=True)
        self.assertEqual(requisicion.estado, 'pendiente_director')
        self.assertEqual(requisicion.administrador_centro, self.admin_centro)
        
        # 4. Director autoriza y envía a farmacia
        requisicion.cambiar_estado_con_historial(
            'enviada',
            usuario=self.director,
            motivo='Aprobado por dirección'
        )
        requisicion.save(skip_validation=True)
        self.assertEqual(requisicion.estado, 'enviada')
        self.assertEqual(requisicion.director_centro, self.director)
        
        # 5. Farmacia recibe
        requisicion.cambiar_estado_con_historial(
            'en_revision',
            usuario=self.farmacia,
            motivo='Recibido para revisión'
        )
        requisicion.save(skip_validation=True)
        self.assertEqual(requisicion.estado, 'en_revision')
        self.assertEqual(requisicion.receptor_farmacia, self.farmacia)
        
        # 6. Farmacia autoriza
        requisicion.cambiar_estado_con_historial(
            'autorizada',
            usuario=self.farmacia,
            motivo='Autorizado para surtido'
        )
        requisicion.save(skip_validation=True)
        self.assertEqual(requisicion.estado, 'autorizada')
        self.assertEqual(requisicion.autorizador_farmacia, self.farmacia)
        
        # Verificar historial completo
        historial_count = RequisicionHistorialEstados.objects.filter(
            requisicion=requisicion
        ).count()
        self.assertEqual(historial_count, 5)  # 5 transiciones
    
    def test_no_puede_saltar_pasos(self):
        """ISS-006: No se pueden saltar pasos del flujo."""
        requisicion = Requisicion.objects.create(
            numero='REQ-FLUJO-002',
            estado='borrador',
            centro_origen=self.centro,
            solicitante=self.medico
        )
        
        # Intentar saltar directamente a 'autorizada'
        with self.assertRaises(ValidationError):
            requisicion.cambiar_estado('autorizada', usuario=self.farmacia)
        
        # Verificar que el estado no cambió
        self.assertEqual(requisicion.estado, 'borrador')
    
    def test_cancelacion_desde_estados_permitidos(self):
        """ISS-006: Cancelación solo desde estados que lo permiten."""
        requisicion = Requisicion.objects.create(
            numero='REQ-FLUJO-003',
            estado='borrador',
            centro_origen=self.centro,
            solicitante=self.medico
        )
        
        # Verificar que puede cancelar desde borrador
        self.assertTrue(requisicion.puede_transicionar_a('cancelada'))
        
        # Cancelar
        requisicion.cambiar_estado_con_historial(
            'cancelada',
            usuario=self.medico,
            motivo='Ya no se necesita'
        )
        requisicion.save(skip_validation=True)
        
        # Verificar que es terminal
        self.assertTrue(requisicion.es_estado_terminal())
        self.assertEqual(len(requisicion.get_transiciones_disponibles()), 0)
