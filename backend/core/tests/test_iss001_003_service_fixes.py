"""
Tests para correcciones ISS-001, ISS-002, ISS-003 en RequisicionService

ISS-001: validar_stock_disponible SOLO considera farmacia central
ISS-002: surtir SOLO consume de farmacia central  
ISS-003: CentroPermissionMixin usa catálogo real de roles
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.test import TestCase
from unittest.mock import MagicMock, patch

from core.models import (
    User, Centro, Producto, Lote, Requisicion, DetalleRequisicion
)
from inventario.services import (
    RequisicionService,
    StockInsuficienteError,
    CentroPermissionMixin,
)


class ISS001ValidacionStockTest(TestCase):
    """ISS-001: Validación de stock SOLO desde farmacia central"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='farmacia_iss001',
            email='farmacia@test.com',
            password='test123!',
            rol='farmacia'
        )
        cls.centro = Centro.objects.create(
            clave='CTR001',
            nombre='Centro Test ISS001',
            direccion='Test Address'
        )
        cls.producto = Producto.objects.create(
            clave='MED001',
            descripcion='Medicamento Test ISS001',
            unidad_medida='PIEZA',
            stock_minimo=10,
            precio_unitario=Decimal('10.00')
        )
    
    def test_validacion_solo_usa_farmacia_central(self):
        """
        ISS-001 FIX: Si el centro tiene stock pero farmacia central no,
        la validación debe fallar (no debe considerar stock del centro).
        """
        # Primero crear lote en farmacia central para tener lote_origen
        lote_fc = Lote.objects.create(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOT-ORIGEN-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=0,  # Farmacia central está agotada
            estado='agotado'
        )
        
        # Stock SOLO en centro destino (vinculado a lote origen)
        Lote.objects.create(
            producto=self.producto,
            centro=self.centro,  # Stock en centro (NO farmacia central)
            numero_lote='LOT-ORIGEN-001',
            lote_origen=lote_fc,  # Vinculado al lote de farmacia
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Crear requisición que pide 50 unidades
        req = Requisicion.objects.create(
            folio='REQ-ISS001-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=50,
            cantidad_autorizada=50
        )
        
        service = RequisicionService(req, self.user)
        
        # DEBE fallar porque farmacia central NO tiene stock
        with self.assertRaises(StockInsuficienteError) as ctx:
            service.validar_stock_disponible()
        
        self.assertIn('Stock insuficiente', str(ctx.exception))
    
    def test_validacion_usa_farmacia_central_correctamente(self):
        """
        ISS-001 FIX: Si farmacia central tiene stock suficiente,
        la validación debe pasar aunque el centro no tenga nada.
        """
        # Stock en farmacia central (centro=NULL)
        Lote.objects.create(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOT-FC-001',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        # Crear requisición que pide 50 unidades
        req = Requisicion.objects.create(
            folio='REQ-ISS001-002',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=50,
            cantidad_autorizada=50
        )
        
        service = RequisicionService(req, self.user)
        
        # NO debe fallar - farmacia central tiene stock
        result = service.validar_stock_disponible()
        self.assertEqual(result, [])  # Sin errores


class ISS002SurtidoSoloFarmaciaCentralTest(TestCase):
    """ISS-002: Surtido SOLO consume de farmacia central"""
    
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='farmacia_iss002',
            email='farmacia2@test.com',
            password='test123!',
            rol='farmacia'
        )
        cls.centro = Centro.objects.create(
            clave='CTR002',
            nombre='Centro Test ISS002',
            direccion='Test Address'
        )
        cls.producto = Producto.objects.create(
            clave='MED002',
            descripcion='Medicamento Test ISS002',
            unidad_medida='PIEZA',
            stock_minimo=10,
            precio_unitario=Decimal('10.00')
        )
    
    def test_surtido_no_consume_stock_centro_destino(self):
        """
        ISS-002 FIX: El surtido NO debe consumir stock del centro destino.
        Si solo hay stock en el centro, debe fallar.
        """
        # Crear lote origen en farmacia central (agotado)
        lote_fc = Lote.objects.create(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOT-FC-AGOTADO',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=0,  # Agotado
            estado='agotado'
        )
        
        # Stock SOLO en centro destino (vinculado al lote origen)
        lote_centro = Lote.objects.create(
            producto=self.producto,
            centro=self.centro,  # Stock en centro
            numero_lote='LOT-FC-AGOTADO',
            lote_origen=lote_fc,
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        req = Requisicion.objects.create(
            folio='REQ-ISS002-001',
            centro=self.centro,
            usuario_solicita=self.user,
            estado='autorizada'
        )
        DetalleRequisicion.objects.create(
            requisicion=req,
            producto=self.producto,
            cantidad_solicitada=50,
            cantidad_autorizada=50
        )
        
        service = RequisicionService(req, self.user)
        
        # DEBE fallar porque farmacia central no tiene stock
        with self.assertRaises(StockInsuficienteError):
            service.surtir(
                is_farmacia_or_admin_fn=lambda u: True,
                get_user_centro_fn=lambda u: None
            )
        
        # Verificar que stock del centro NO fue modificado
        lote_centro.refresh_from_db()
        self.assertEqual(lote_centro.cantidad_actual, 100)  # Sin cambios
    
    def test_surtido_consume_farmacia_central_y_crea_en_centro(self):
        """
        ISS-002 FIX: El surtido debe consumir de farmacia central
        y crear entrada en centro destino.
        """
        # Stock en farmacia central
        lote_fc = Lote.objects.create(
            producto=self.producto,
            centro=None,  # Farmacia central
            numero_lote='LOT-FC-ISS002',
            fecha_caducidad=timezone.now().date() + timedelta(days=365),
            cantidad_inicial=100,
            cantidad_actual=100,
            estado='disponible'
        )
        
        req = Requisicion.objects.create(
            folio='REQ-ISS002-002',
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
        result = service.surtir(
            is_farmacia_or_admin_fn=lambda u: True,
            get_user_centro_fn=lambda u: None
        )
        
        # Verificar que se descontó de farmacia central
        lote_fc.refresh_from_db()
        self.assertEqual(lote_fc.cantidad_actual, 70)  # 100 - 30
        
        # Verificar que se creó lote en centro destino
        lote_destino = Lote.objects.filter(
            producto=self.producto,
            centro=self.centro,
            numero_lote='LOT-FC-ISS002'
        ).first()
        self.assertIsNotNone(lote_destino)
        self.assertEqual(lote_destino.cantidad_actual, 30)
        
        # Verificar resultado
        self.assertTrue(result['exito'])
        self.assertEqual(result['estado'], 'surtida')


class ISS003RolesAccesoGlobalTest(TestCase):
    """ISS-003: CentroPermissionMixin usa catálogo real de roles"""
    
    def setUp(self):
        self.mixin = CentroPermissionMixin()
        self.mixin.request = MagicMock()
        self.mixin.request.data = {}
        self.mixin.request.query_params = {}
    
    def test_roles_globales_correctos(self):
        """ISS-003 FIX: Verificar que el catálogo de roles es correcto"""
        roles_esperados = {
            'admin_sistema', 'superusuario', 'administrador',
            'farmacia', 'admin_farmacia', 'farmaceutico', 'usuario_farmacia',
            'vista', 'usuario_vista',
        }
        
        # Verificar que el mixin tiene los roles correctos
        self.assertEqual(
            CentroPermissionMixin.ROLES_ACCESO_GLOBAL,
            roles_esperados
        )
    
    def test_admin_sistema_tiene_acceso_global(self):
        """ISS-003 FIX: admin_sistema debe tener acceso a cualquier centro"""
        user = MagicMock()
        user.is_superuser = False
        user.rol = 'admin_sistema'
        self.mixin.request.user = user
        
        # No debe lanzar excepción
        self.mixin.check_centro_permission(centro_id=999)
    
    def test_admin_farmacia_tiene_acceso_global(self):
        """ISS-003 FIX: admin_farmacia debe tener acceso a cualquier centro"""
        user = MagicMock()
        user.is_superuser = False
        user.rol = 'admin_farmacia'
        self.mixin.request.user = user
        
        # No debe lanzar excepción
        self.mixin.check_centro_permission(centro_id=999)
    
    def test_farmacia_tiene_acceso_global(self):
        """ISS-003 FIX: farmacia debe tener acceso a cualquier centro"""
        user = MagicMock()
        user.is_superuser = False
        user.rol = 'farmacia'
        self.mixin.request.user = user
        
        # No debe lanzar excepción
        self.mixin.check_centro_permission(centro_id=999)
    
    def test_usuario_centro_sin_acceso_a_otro_centro(self):
        """ISS-003: Usuario de centro NO tiene acceso a otros centros"""
        from rest_framework.exceptions import PermissionDenied
        
        user = MagicMock()
        user.is_superuser = False
        user.rol = 'usuario_centro'
        user.centro = MagicMock()
        user.centro.pk = 1  # Centro asignado
        self.mixin.request.user = user
        
        # Debe lanzar excepción al acceder a centro diferente
        with self.assertRaises(PermissionDenied):
            self.mixin.check_centro_permission(centro_id=999)  # Otro centro
    
    def test_usuario_centro_accede_a_su_centro(self):
        """ISS-003: Usuario de centro SÍ tiene acceso a su propio centro"""
        user = MagicMock()
        user.is_superuser = False
        user.rol = 'usuario_centro'
        user.centro = MagicMock()
        user.centro.pk = 1
        self.mixin.request.user = user
        
        # No debe lanzar excepción
        self.mixin.check_centro_permission(centro_id=1)  # Su centro
    
    def test_rol_inexistente_admin_no_tiene_acceso(self):
        """ISS-003 FIX: El rol 'admin' (obsoleto) NO debe tener acceso global"""
        from rest_framework.exceptions import PermissionDenied
        
        user = MagicMock()
        user.is_superuser = False
        user.rol = 'admin'  # Rol obsoleto que NO está en ROLES_ACCESO_GLOBAL
        user.centro = None  # Sin centro asignado
        self.mixin.request.user = user
        
        # Debe lanzar excepción porque 'admin' no es rol válido
        with self.assertRaises(PermissionDenied):
            self.mixin.check_centro_permission(centro_id=999)
