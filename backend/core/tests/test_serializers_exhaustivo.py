"""Tests exhaustivos para serializers - validaciones basicas."""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from core.models import Centro, Producto, Lote, Requisicion, DetalleRequisicion
from core.serializers import (
    ProductoSerializer,
    LoteSerializer,
    RequisicionSerializer,
    DetalleRequisicionSerializer,
)

User = get_user_model()


class ProductoSerializerTestExhaustivo(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='test123')

    def test_serializar_producto(self):
        prod = Producto.objects.create(
            clave='PROD001',
            descripcion='Producto Test Completo',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('99.99'),
            stock_minimo=5,
            activo=True,
            created_by=self.usuario,
        )
        data = ProductoSerializer(prod).data
        self.assertEqual(data['clave'], 'PROD001')
        self.assertEqual(data['precio_unitario'], '99.99')

    def test_validacion_precio_negativo(self):
        data = {
            'clave': 'TEST001',
            'descripcion': 'Descripcion valida',
            'unidad_medida': 'PIEZA',
            'precio_unitario': '-1.00',
            'stock_minimo': 1,
        }
        serializer = ProductoSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('precio_unitario', serializer.errors)


class LoteSerializerTestExhaustivo(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='testuser', password='test123')
        self.producto = Producto.objects.create(
            clave='PROD001',
            descripcion='Producto Test',
            unidad_medida='PIEZA',
            precio_unitario=Decimal('100.00'),
            created_by=self.usuario,
        )

    def test_validacion_cantidad_actual(self):
        data = {
            'producto': self.producto.id,
            'numero_lote': 'LOT001',
            'fecha_caducidad': (date.today() + timedelta(days=30)).isoformat(),
            'cantidad_inicial': 10,
            'cantidad_actual': 20,
        }
        serializer = LoteSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class RequisicionSerializerTestExhaustivo(TestCase):
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

    def test_serializar_requisicion_con_detalles(self):
        # Usar campos reales: numero, solicitante, centro_destino
        req = Requisicion.objects.create(numero='TEST-SER-001', solicitante=self.usuario, centro_destino=self.centro)
        DetalleRequisicion.objects.create(requisicion=req, producto=self.producto, cantidad_solicitada=5)
        data = RequisicionSerializer(req).data
        self.assertEqual(len(data['detalles']), 1)
        self.assertEqual(data['detalles'][0]['cantidad_solicitada'], 5)

    def test_validacion_detalle_requisicion(self):
        data = {
            'producto': self.producto.id,
            'cantidad_solicitada': 0,  # invalido
        }
        serializer = DetalleRequisicionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
