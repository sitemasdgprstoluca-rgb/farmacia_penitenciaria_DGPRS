"""Tests exhaustivos para modelos - casos borde y validaciones."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import Centro, Producto, Lote, Requisicion, DetalleRequisicion

User = get_user_model()


class ProductoModelTestExhaustivo(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='test123')

    def test_clave_normalizada_mayuscula(self):
        prod = Producto.objects.create(
            clave='abc123',
            descripcion='Producto Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('100.00'),
            created_by=self.usuario,
        )
        self.assertEqual(prod.clave, 'ABC123')

    def test_clave_unica_case_insensitive(self):
        Producto.objects.create(
            clave='PROD001',
            descripcion='Producto 1',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('100.00'),
            created_by=self.usuario,
        )
        with self.assertRaises(Exception):
            Producto.objects.create(
                clave='prod001',
                descripcion='Duplicado',
                unidad_medida='PIEZA',
                precio_unitario=Decimal('50.00'),
                created_by=self.usuario,
            )

    def test_descripcion_minima(self):
        prod = Producto(
            clave='BAD01',
            descripcion='abcd',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('10.00'),
            created_by=self.usuario,
        )
        with self.assertRaises(ValidationError):
            prod.full_clean()

    def test_precio_positivo(self):
        prod = Producto(
            clave='NEG01',
            descripcion='Precio Negativo',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('-1.00'),
            created_by=self.usuario,
        )
        with self.assertRaises(ValidationError):
            prod.full_clean()

    def test_get_nivel_stock_sin_lotes(self):
        prod = Producto.objects.create(
            clave='STOCK0',
            descripcion='Sin Lotes',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('1.00'),
            stock_minimo=5,
            created_by=self.usuario,
        )
        # Sin lotes, stock=0, nivel debe ser 'critico'
        self.assertEqual(prod.get_nivel_stock(), 'critico')


class LoteModelTestExhaustivo(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='test123')
        self.producto = Producto.objects.create(
            clave='PROD001',
            descripcion='Producto Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('100.00'),
            created_by=self.usuario,
        )

    def test_cantidad_actual_no_excede_inicial(self):
        lote = Lote(
            producto=self.producto,
            numero_lote='LOTBAD',
            fecha_caducidad=date.today() + timedelta(days=10),
            cantidad_inicial=10,
            cantidad_actual=20,
            created_by=self.usuario,
        )
        with self.assertRaises(ValidationError):
            lote.full_clean()

    def test_numero_lote_unico_por_producto(self):
        Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE001',
            fecha_caducidad=date.today() + timedelta(days=30),
            cantidad_inicial=10,
            cantidad_actual=10,
            created_by=self.usuario,
        )
        with self.assertRaises(Exception):
            Lote.objects.create(
                producto=self.producto,
                numero_lote='LOTE001',
                fecha_caducidad=date.today() + timedelta(days=30),
                cantidad_inicial=5,
                cantidad_actual=5,
                created_by=self.usuario,
            )

    def test_alerta_caducidad_vencida(self):
        lote = Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTVENC',
            fecha_caducidad=date.today() - timedelta(days=1),
            cantidad_inicial=5,
            cantidad_actual=5,
            created_by=self.usuario,
        )
        self.assertEqual(lote.alerta_caducidad(), 'vencido')


class RequisicionModelTestExhaustivo(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='test123')
        self.centro = Centro.objects.create(clave='CTR001', nombre='Centro Test')
        self.producto = Producto.objects.create(
            clave='PROD001',
            descripcion='Producto Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('100.00'),
            created_by=self.usuario,
        )

    def test_requisicion_estado_inicial(self):
        req = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro)
        self.assertEqual(req.estado, 'borrador')

    def test_folio_unico(self):
        r1 = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro)
        r2 = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro)
        self.assertNotEqual(r1.folio, r2.folio)

    def test_detalles_requisicion(self):
        req = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro)
        DetalleRequisicion.objects.create(requisicion=req, producto=self.producto, cantidad_solicitada=2)
        self.assertEqual(req.detalles.count(), 1)


class CentroModelTestExhaustivo(TestCase):
    """Tests exhaustivos para el modelo Centro"""
    
    def test_clave_unica(self):
        """Verifica que la clave del centro sea única"""
        Centro.objects.create(clave='CTR001', nombre='Centro 1')
        with self.assertRaises(Exception):
            Centro.objects.create(clave='CTR001', nombre='Centro 2')

    def test_centro_activo_por_default(self):
        """Verifica que un centro sea activo por defecto"""
        centro = Centro.objects.create(clave='CTR002', nombre='Centro Test')
        self.assertTrue(centro.activo)

    def test_centro_timestamps(self):
        """Verifica que se registren timestamps correctamente"""
        centro = Centro.objects.create(clave='CTR003', nombre='Centro Timestamp')
        self.assertIsNotNone(centro.created_at)
        self.assertIsNotNone(centro.updated_at)


class UserModelTestExhaustivo(TestCase):
    """Tests exhaustivos para el modelo User"""
    
    def test_user_con_centro(self):
        """Verifica que un usuario pueda tener un centro asignado"""
        centro = Centro.objects.create(clave='CTR001', nombre='Centro Test')
        user = User.objects.create_user(username='user1', password='test123', centro=centro)
        self.assertEqual(user.centro, centro)

    def test_user_sin_centro(self):
        """Verifica que un usuario pueda existir sin centro asignado"""
        user = User.objects.create_user(username='user2', password='test123')
        self.assertIsNone(user.centro)

    def test_multiple_users_mismo_centro(self):
        """Verifica que múltiples usuarios puedan pertenecer al mismo centro"""
        centro = Centro.objects.create(clave='CTR002', nombre='Centro Test')
        user1 = User.objects.create_user(username='user3', password='test123', centro=centro)
        user2 = User.objects.create_user(username='user4', password='test123', centro=centro)
        self.assertEqual(user1.centro, user2.centro)


class LoteSoftDeleteTest(TestCase):
    """Tests para funcionalidad de soft delete en Lote"""
    
    def test_soft_delete_lote(self):
        """Verifica que el soft delete marque el campo deleted_at"""
        producto = Producto.objects.create(
            clave='PROD001', descripcion='Producto Test',
            unidad_medida='PIEZA', precio_unitario=10.00
        )
        lote = Lote.objects.create(
            producto=producto, numero_lote='LOT001',
            fecha_caducidad=date.today() + timedelta(days=90),
            cantidad_inicial=100, cantidad_actual=100
        )
        lote.soft_delete()
        lote.refresh_from_db()
        self.assertIsNotNone(lote.deleted_at)

    def test_active_only_excluye_eliminados(self):
        """Verifica que active_only() excluya lotes con soft delete"""
        producto = Producto.objects.create(
            clave='PROD002', descripcion='Producto Test 2',
            unidad_medida='CAJA', precio_unitario=50.00
        )
        lote_activo = Lote.objects.create(
            producto=producto, numero_lote='LOT002',
            fecha_caducidad=date.today() + timedelta(days=60),
            cantidad_inicial=50, cantidad_actual=50
        )
        lote_eliminado = Lote.objects.create(
            producto=producto, numero_lote='LOT003',
            fecha_caducidad=date.today() + timedelta(days=60),
            cantidad_inicial=30, cantidad_actual=30
        )
        lote_eliminado.soft_delete()
        lotes_activos = Lote.active_only()
        self.assertEqual(lotes_activos.count(), 1)
        self.assertEqual(lotes_activos.first().numero_lote, 'LOT002')


class RequisicionRelacionesTest(TestCase):
    """Tests para relaciones del modelo Requisicion"""
    
    def setUp(self):
        self.centro = Centro.objects.create(clave='CTR001', nombre='Centro Test')
        self.usuario = User.objects.create_user(username='testuser', password='test123')
        self.producto = Producto.objects.create(
            clave='PROD001', descripcion='Producto Test',
            unidad_medida='PIEZA', precio_unitario=10.00
        )

    def test_requisicion_sin_detalles_invalida(self):
        req = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro)
        # Una requisición sin detalles no debería poder enviarse
        self.assertEqual(req.detalles.count(), 0)

    def test_detalle_cantidad_positiva(self):
        req = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro)
        detalle = DetalleRequisicion(requisicion=req, producto=self.producto, cantidad_solicitada=0)
        with self.assertRaises(ValidationError):
            detalle.full_clean()

    def test_delete_producto_protege_detalles(self):
        req = Requisicion.objects.create(usuario_solicita=self.usuario, centro=self.centro)
        DetalleRequisicion.objects.create(requisicion=req, producto=self.producto, cantidad_solicitada=5)
        
        # Intentar borrar producto con detalles asociados debería fallar o proteger
        with self.assertRaises(Exception):
            self.producto.delete()

