"""
Tests para correcciones ISS-001 a ISS-008 (segundo reporte de auditoría)

ISS-001: cambiar_estado persiste cambios con auditoría
ISS-002: Filtro de caducidad en surtido (lotes vencidos no se usan)
ISS-003: Bloqueo de requisición para evitar doble surtido
ISS-005: Validación cantidad surtida <= autorizada
ISS-006: Trazabilidad updated_by en cambios de estado
ISS-008: Estados terminales no permiten modificaciones
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from unittest.mock import MagicMock, patch
import threading
import time

from core.models import (
    User, Centro, Producto, Lote, Requisicion, DetalleRequisicion
)
from inventario.services import (
    RequisicionService,
    StockInsuficienteError,
    EstadoInvalidoError,
)


class BaseTestCase(TestCase):
    """Base con fixtures comunes"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='test_auditoria',
            email='test@test.com',
            password='test123!',
            rol='farmacia'
        )
        cls.user_centro = User.objects.create_user(
            username='user_centro',
            email='centro@test.com',
            password='test123!',
            rol='usuario_centro'
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


class ISS001CambiarEstadoPersistenciaTest(BaseTestCase):
    """ISS-001: cambiar_estado debe persistir cambios automáticamente"""
    
    def test_cambiar_estado_persiste_automaticamente(self):
        """El cambio de estado se guarda en BD sin llamar save() explícito"""
        req = Requisicion.objects.create(
            folio='REQ-PERSIST-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='borrador'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=10
        )
        
        # Cambiar estado
        req.cambiar_estado('enviada', usuario=self.user)
        
        # Verificar que se persistió sin necesidad de save()
        req_db = Requisicion.objects.get(pk=req.pk)
        self.assertEqual(req_db.estado, 'enviada')
    
    def test_cambiar_estado_registra_updated_by(self):
        """ISS-006: El cambio de estado registra quién lo hizo"""
        req = Requisicion.objects.create(
            folio='REQ-AUDIT-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='borrador'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=10
        )
        
        req.cambiar_estado('enviada', usuario=self.user_centro)
        
        req_db = Requisicion.objects.get(pk=req.pk)
        self.assertEqual(req_db.updated_by, self.user_centro)
    
    def test_cambiar_estado_persist_false_no_guarda(self):
        """Con persist=False no se guardan cambios automáticamente"""
        req = Requisicion.objects.create(
            folio='REQ-NOPERSIST-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='borrador'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=10
        )
        
        req.cambiar_estado('enviada', usuario=self.user, persist=False)
        
        # Estado local cambió
        self.assertEqual(req.estado, 'enviada')
        
        # Pero BD no cambió
        req_db = Requisicion.objects.get(pk=req.pk)
        self.assertEqual(req_db.estado, 'borrador')


class ISS008EstadosTerminalesTest(BaseTestCase):
    """ISS-008: Estados terminales no permiten modificaciones"""
    
    def test_estado_cancelada_no_permite_cambios(self):
        """No se puede cambiar el estado de una requisición cancelada"""
        req = Requisicion.objects.create(
            folio='REQ-TERMINAL-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='cancelada'  # Estado terminal
        )
        
        with self.assertRaises(ValidationError) as ctx:
            req.cambiar_estado('borrador', usuario=self.user)
        
        self.assertIn('estado terminal', str(ctx.exception).lower())
    
    def test_estado_recibida_no_permite_cambios(self):
        """No se puede cambiar el estado de una requisición recibida"""
        req = Requisicion.objects.create(
            folio='REQ-TERMINAL-002',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='recibida'  # Estado terminal
        )
        
        with self.assertRaises(ValidationError) as ctx:
            req.cambiar_estado('surtida', usuario=self.user)
        
        self.assertIn('estado terminal', str(ctx.exception).lower())


class ISS002CaducidadEnSurtidoTest(BaseTestCase):
    """ISS-002: Lotes caducados no deben usarse en surtido"""
    
    def setUp(self):
        # Lote CADUCADO (fecha pasada)
        self.lote_caducado = Lote.objects.create(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOT-CADUCADO-001',
            fecha_caducidad=timezone.now().date() - timedelta(days=1),  # Ayer
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'  # Aún disponible pero caducado
        )
        
        # Lote VIGENTE
        self.lote_vigente = Lote.objects.create(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOT-VIGENTE-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible'
        )
    
    def test_validacion_stock_ignora_lotes_caducados(self):
        """La validación de stock solo cuenta lotes vigentes"""
        req = Requisicion.objects.create(
            folio='REQ-CADUCIDAD-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=100,  # Requiere más que el lote vigente
            cantidad_autorizada=100
        )
        
        service = RequisicionService(req, self.user)
        
        # Solo hay 50 vigentes (100 caducados no cuentan)
        with self.assertRaises(StockInsuficienteError) as ctx:
            service.validar_stock_disponible()
        
        # Verificar que solo contó 50 disponibles
        self.assertEqual(ctx.exception.detalles_stock[0]['disponible'], 50)
    
    def test_surtido_usa_solo_lotes_vigentes(self):
        """El surtido solo consume de lotes vigentes, no caducados"""
        req = Requisicion.objects.create(
            folio='REQ-CADUCIDAD-002',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=30,
            cantidad_autorizada=30
        )
        
        service = RequisicionService(req, self.user)
        resultado = service.surtir(
            is_farmacia_or_admin_fn=lambda u: True,
            get_user_centro_fn=lambda u: None
        )
        
        # Verificar que se usó el lote vigente
        self.lote_vigente.refresh_from_db()
        self.assertEqual(self.lote_vigente.cantidad_actual, 20)  # 50 - 30
        
        # Verificar que el lote caducado NO fue tocado
        self.lote_caducado.refresh_from_db()
        self.assertEqual(self.lote_caducado.cantidad_actual, 100)  # Sin cambios


class ISS003BloqueoRequisicionTest(TransactionTestCase):
    """ISS-003: Bloqueo de requisición para evitar doble surtido"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_concurrencia',
            email='conc@test.com',
            password='test123!',
            rol='farmacia'
        )
        self.centro = Centro.objects.create(
            clave='CTR002',
            nombre='Centro Concurrencia',
            direccion='Test Address'
        )
        self.producto = Producto.objects.create(
            clave='MED002',
            descripcion='Medicamento Concurrencia',
            unidad_medida='PIEZA',
            stock_minimo=10,
            precio_unitario=Decimal('10.00')
        )
        # Stock suficiente para UN surtido, no dos
        self.lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-CONC-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=50,
            cantidad_actual=50,
            estado='disponible'
        )
        self.req = Requisicion.objects.create(
            folio='REQ-CONC-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=self.req,
            producto=self.producto,
            cantidad_solicitada=50,
            cantidad_autorizada=50
        )
    
    def test_doble_surtido_bloqueado(self):
        """Dos surtidos simultáneos: uno debe fallar"""
        resultados = {'thread1': None, 'thread2': None}
        errores = {'thread1': None, 'thread2': None}
        
        def surtir_thread(nombre):
            try:
                req = Requisicion.objects.get(pk=self.req.pk)
                service = RequisicionService(req, self.user)
                resultado = service.surtir(
                    is_farmacia_or_admin_fn=lambda u: True,
                    get_user_centro_fn=lambda u: None
                )
                resultados[nombre] = resultado
            except Exception as e:
                errores[nombre] = e
        
        # Ejecutar dos threads simultáneos
        t1 = threading.Thread(target=surtir_thread, args=('thread1',))
        t2 = threading.Thread(target=surtir_thread, args=('thread2',))
        
        t1.start()
        t2.start()
        
        t1.join(timeout=10)
        t2.join(timeout=10)
        
        # Al menos uno debe haber tenido éxito y al menos uno debe fallar o 
        # el segundo debe encontrar estado ya cambiado
        exitos = sum(1 for r in resultados.values() if r is not None)
        fallos = sum(1 for e in errores.values() if e is not None)
        
        # El lote debe tener exactamente 0 (un solo surtido exitoso de 50)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.cantidad_actual, 0)
        
        # La requisición debe estar surtida
        self.req.refresh_from_db()
        self.assertEqual(self.req.estado, 'surtida')


class ISS005CantidadAutorizadaTest(BaseTestCase):
    """ISS-005: Cantidad surtida no puede exceder autorizada"""
    
    def test_no_surte_mas_de_lo_autorizado(self):
        """El surtido no puede exceder la cantidad autorizada"""
        # Crear lote con mucho stock
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-AUTH-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=1000,
            cantidad_actual=1000,
            estado='disponible'
        )
        
        req = Requisicion.objects.create(
            folio='REQ-AUTH-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        detalle = DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=100,
            cantidad_autorizada=50,  # Solo autorizado 50
            cantidad_surtida=0
        )
        
        service = RequisicionService(req, self.user)
        resultado = service.surtir(
            is_farmacia_or_admin_fn=lambda u: True,
            get_user_centro_fn=lambda u: None
        )
        
        # Verificar que solo se surtió lo autorizado
        detalle.refresh_from_db()
        self.assertEqual(detalle.cantidad_surtida, 50)  # No más de autorizado
        
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, 950)  # 1000 - 50
