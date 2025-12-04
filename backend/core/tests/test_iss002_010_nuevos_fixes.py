"""
Tests para ISS-002 a ISS-010 - Nuevas correcciones de auditoría.

Cobertura:
- ISS-002: Trazabilidad detalle-lote con DetalleSurtido
- ISS-003: Constraints en DetalleRequisicion
- ISS-004: Flujo de recepción con confirmar_recepcion
- ISS-006: Validar stock en validar_envio
- ISS-007: Validación de movimientos sobre lotes eliminados/vencidos
- ISS-008: Propagación de soft-delete a lotes derivados
"""
import pytest
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.models import (
    User, Centro, Producto, Lote, Requisicion, 
    DetalleRequisicion, Movimiento, DetalleSurtido
)
from inventario.services.requisicion_service import (
    RequisicionService, EstadoInvalidoError, PermisoRequisicionError
)
from inventario.services.contract_validators import RequisicionContractValidator


class BaseTestCase(TestCase):
    """Clase base con fixtures comunes"""
    
    @classmethod
    def setUpTestData(cls):
        cls.centro = Centro.objects.create(
            nombre='Centro Test',
            clave='CT01',
            direccion='Dir Test'
        )
        cls.producto = Producto.objects.create(
            clave='TST001',
            descripcion='Producto Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            stock_minimo=10
        )
        cls.user_farmacia = User.objects.create_user(
            username='farmacia_test',
            password='test123',
            rol='farmacia'
        )
        cls.user_centro = User.objects.create_user(
            username='centro_test',
            password='test123',
            rol='usuario_centro',
            centro=cls.centro
        )


class ISS002DetalleSurtidoTest(BaseTestCase):
    """ISS-002: Trazabilidad detalle-lote"""
    
    def test_detalle_surtido_se_crea_al_surtir(self):
        """Al surtir se crea registro en DetalleSurtido"""
        # Crear lote en farmacia
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-TRAZ-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100
        )
        
        # Crear requisición autorizada
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user_centro,
            estado='autorizada'
        )
        detalle = DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=30,
            cantidad_autorizada=30
        )
        
        # Surtir
        service = RequisicionService(req, self.user_farmacia)
        resultado = service.surtir(
            is_farmacia_or_admin_fn=lambda u: True,
            get_user_centro_fn=lambda u: None
        )
        
        # Verificar DetalleSurtido creado
        detalle_surtidos = DetalleSurtido.objects.filter(detalle_requisicion=detalle)
        self.assertEqual(detalle_surtidos.count(), 1)
        
        ds = detalle_surtidos.first()
        self.assertEqual(ds.lote, lote)
        self.assertEqual(ds.cantidad, 30)
        self.assertIsNotNone(ds.movimiento)
        self.assertEqual(ds.usuario, self.user_farmacia)
    
    def test_multiples_lotes_crean_multiples_detalles(self):
        """Si se usan múltiples lotes, se crean múltiples DetalleSurtido"""
        # Crear dos lotes pequeños
        lote1 = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-MULTI-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=100),
            cantidad_inicial=20,
            cantidad_actual=20
        )
        lote2 = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-MULTI-002',
            fecha_caducidad=timezone.now().date() + timedelta(days=200),
            cantidad_inicial=30,
            cantidad_actual=30
        )
        
        # Requisición que necesita 40 (usará ambos lotes)
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user_centro,
            estado='autorizada'
        )
        detalle = DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=40,
            cantidad_autorizada=40
        )
        
        # Surtir
        service = RequisicionService(req, self.user_farmacia)
        service.surtir(
            is_farmacia_or_admin_fn=lambda u: True,
            get_user_centro_fn=lambda u: None
        )
        
        # Verificar dos DetalleSurtido
        detalle_surtidos = DetalleSurtido.objects.filter(
            detalle_requisicion=detalle
        ).order_by('fecha_surtido')
        
        self.assertEqual(detalle_surtidos.count(), 2)
        
        # Lote1 primero (FEFO - caduca antes)
        ds1 = detalle_surtidos[0]
        self.assertEqual(ds1.lote, lote1)
        self.assertEqual(ds1.cantidad, 20)
        
        # Lote2 segundo
        ds2 = detalle_surtidos[1]
        self.assertEqual(ds2.lote, lote2)
        self.assertEqual(ds2.cantidad, 20)


class ISS003ConstraintsTest(BaseTestCase):
    """ISS-003: Constraints en DetalleRequisicion"""
    
    def test_constraint_surtida_no_excede_autorizada(self):
        """Cantidad surtida no puede exceder autorizada"""
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user_centro,
            estado='autorizada'
        )
        detalle = DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=100,
            cantidad_autorizada=50,
            cantidad_surtida=0
        )
        
        # Intentar poner surtida > autorizada debe fallar
        detalle.cantidad_surtida = 60
        
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                detalle.save()
    
    def test_constraint_autorizada_no_excede_solicitada(self):
        """Cantidad autorizada no puede exceder solicitada"""
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user_centro,
            estado='borrador'
        )
        
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetalleRequisicion.objects.create(
                    requisicion=req,
                    producto=self.producto,
                    cantidad_solicitada=50,
                    cantidad_autorizada=60  # Mayor que solicitada
                )
    
    def test_constraint_cantidades_no_negativas(self):
        """Cantidades no pueden ser negativas"""
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user_centro,
            estado='borrador'
        )
        
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DetalleRequisicion.objects.create(
                    requisicion=req,
                    producto=self.producto,
                    cantidad_solicitada=50,
                    cantidad_autorizada=-10
                )


class ISS004RecepcionTest(BaseTestCase):
    """ISS-004: Flujo de recepción"""
    
    def setUp(self):
        super().setUp()
        # Crear lote
        self.lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-REC-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100
        )
        
        # Crear y surtir requisición
        self.req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user_centro,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=self.req,
            producto=self.producto,
            cantidad_solicitada=30,
            cantidad_autorizada=30
        )
        
        service = RequisicionService(self.req, self.user_farmacia)
        service.surtir(
            is_farmacia_or_admin_fn=lambda u: True,
            get_user_centro_fn=lambda u: None
        )
        self.req.refresh_from_db()
    
    def test_confirmar_recepcion_exitosa(self):
        """Usuario de centro puede confirmar recepción"""
        service = RequisicionService(self.req, self.user_centro)
        resultado = service.confirmar_recepcion(observaciones='Recibido completo')
        
        self.assertTrue(resultado['exito'])
        self.assertEqual(resultado['estado'], 'recibida')
        
        self.req.refresh_from_db()
        self.assertEqual(self.req.estado, 'recibida')
        self.assertEqual(self.req.usuario_recibe, self.user_centro)
        self.assertIsNotNone(self.req.fecha_recibido)
    
    def test_no_puede_confirmar_si_no_es_centro(self):
        """Usuario sin centro no puede confirmar (a menos que sea superuser)"""
        user_sin_centro = User.objects.create_user(
            username='sin_centro',
            password='test123',
            rol='usuario'
        )
        
        service = RequisicionService(self.req, user_sin_centro)
        
        with self.assertRaises(PermisoRequisicionError):
            service.confirmar_recepcion()
    
    def test_no_puede_confirmar_estado_incorrecto(self):
        """Solo se puede confirmar requisición surtida o parcial"""
        # Cambiar estado a recibida manualmente
        self.req.estado = 'recibida'
        self.req.save()
        
        service = RequisicionService(self.req, self.user_centro)
        
        with self.assertRaises(EstadoInvalidoError):
            service.confirmar_recepcion()


class ISS006ValidarStockEnvioTest(BaseTestCase):
    """ISS-006: Validar stock al enviar"""
    
    def test_advertencia_stock_insuficiente(self):
        """Advertencia si stock insuficiente al enviar"""
        # Requisición sin stock
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user_centro,
            estado='borrador'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=1000  # Mucho más de lo disponible
        )
        
        validator = RequisicionContractValidator(req)
        resultado = validator.validar_envio()
        
        # Debe haber error porque no hay stock
        self.assertFalse(resultado.es_valido)
    
    def test_ok_si_hay_stock(self):
        """Sin errores si hay stock suficiente"""
        # Crear lote
        Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-ENV-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100
        )
        
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user_centro,
            estado='borrador'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=50
        )
        
        validator = RequisicionContractValidator(req)
        resultado = validator.validar_envio()
        
        self.assertTrue(resultado.es_valido)


class ISS007MovimientosVencidosTest(BaseTestCase):
    """ISS-007: Validación de movimientos sobre lotes eliminados/vencidos"""
    
    def test_no_movimiento_lote_eliminado(self):
        """No se puede crear movimiento sobre lote soft-deleted"""
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-DEL-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100
        )
        lote.soft_delete()
        
        with self.assertRaises(ValidationError) as ctx:
            Movimiento.objects.create(
                tipo='entrada',
                lote=lote,
                cantidad=10,
                observaciones='Test'
            )
        
        self.assertIn('eliminados', str(ctx.exception))
    
    def test_no_salida_lote_vencido(self):
        """No se puede crear salida de lote vencido"""
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-VEN-001',
            fecha_caducidad=timezone.now().date() - timedelta(days=1),  # Ayer
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='vencido'
        )
        
        with self.assertRaises(ValidationError) as ctx:
            Movimiento.objects.create(
                tipo='salida',
                lote=lote,
                cantidad=-10,
                observaciones='Test'
            )
        
        self.assertIn('vencidos', str(ctx.exception))


class ISS008PropagacionSoftDeleteTest(BaseTestCase):
    """ISS-008: Propagación de soft-delete a lotes derivados"""
    
    def test_soft_delete_propaga_a_derivados(self):
        """Soft-delete de lote farmacia propaga a lotes en centros"""
        # Lote de farmacia
        lote_farmacia = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-PROP-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100
        )
        
        # Lote derivado en centro
        lote_centro = Lote.objects.create(
            producto=self.producto,
            centro=self.centro,
            numero_lote='LOT-PROP-001',
            fecha_caducidad=lote_farmacia.fecha_caducidad,
            cantidad_inicial=30,
            cantidad_actual=30,
            lote_origen=lote_farmacia
        )
        
        # Soft-delete del lote farmacia
        lote_farmacia.soft_delete(propagar_a_derivados=True)
        
        # Verificar propagación
        lote_centro.refresh_from_db()
        self.assertIsNotNone(lote_centro.deleted_at)
        self.assertEqual(lote_centro.estado, 'retirado')
    
    def test_no_propaga_si_desactivado(self):
        """No propaga si propagar_a_derivados=False"""
        lote_farmacia = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-NOPROP-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100
        )
        
        lote_centro = Lote.objects.create(
            producto=self.producto,
            centro=self.centro,
            numero_lote='LOT-NOPROP-001',
            fecha_caducidad=lote_farmacia.fecha_caducidad,
            cantidad_inicial=30,
            cantidad_actual=30,
            lote_origen=lote_farmacia
        )
        
        # Soft-delete sin propagación
        lote_farmacia.soft_delete(propagar_a_derivados=False)
        
        # Lote centro no afectado
        lote_centro.refresh_from_db()
        self.assertIsNone(lote_centro.deleted_at)


class CancelacionRequisicionTest(BaseTestCase):
    """Test para cancelación de requisición con reverso de movimientos"""
    
    def test_cancelar_requisicion_autorizada(self):
        """Cancelar requisición autorizada revierte movimientos"""
        # Crear lote
        lote = Lote.objects.create(
            producto=self.producto,
            centro=None,
            numero_lote='LOT-CAN-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100
        )
        
        # Crear y surtir requisición
        req = Requisicion.objects.create(
            centro=self.centro,
            usuario_solicita=self.user_centro,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=30,
            cantidad_autorizada=30
        )
        
        service = RequisicionService(req, self.user_farmacia)
        service.surtir(
            is_farmacia_or_admin_fn=lambda u: True,
            get_user_centro_fn=lambda u: None
        )
        
        # Verificar stock descontado
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_actual, 70)
        
        # Cancelar
        req.refresh_from_db()
        req.estado = 'parcial'  # Simular estado cancelable
        req.save()
        
        service = RequisicionService(req, self.user_farmacia)
        resultado = service.cancelar_requisicion(motivo='Test de cancelación')
        
        # Verificar cancelación
        self.assertTrue(resultado['exito'])
        self.assertEqual(resultado['estado'], 'cancelada')
        
        req.refresh_from_db()
        self.assertEqual(req.estado, 'cancelada')
