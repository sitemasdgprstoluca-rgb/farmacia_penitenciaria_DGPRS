"""
Tests unitarios e integración para el helper registrar_movimiento_stock.
ISS-003: Cobertura de entradas/salidas/ajustes, validaciones y manejo de errores.
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import serializers
from decimal import Decimal

from core.models import Producto, Lote, Movimiento, Centro
from inventario.views import registrar_movimiento_stock

User = get_user_model()


@pytest.fixture
def producto(db):
    """Crea un producto de prueba."""
    return Producto.objects.create(
        clave='TEST001',
        descripcion='Producto de prueba para tests de stock',
        unidad_medida='PIEZA',
        precio_unitario=Decimal('10.00'),
        stock_minimo=5,
        activo=True
    )


@pytest.fixture
def lote_con_stock(db, producto):
    """Crea un lote con stock disponible."""
    return Lote.objects.create(
        producto=producto,
        numero_lote='LOTE-TEST-001',
        fecha_caducidad='2026-12-31',
        cantidad_inicial=100,
        cantidad_actual=100,
        estado='disponible'
    )


@pytest.fixture
def lote_agotado(db, producto):
    """Crea un lote agotado."""
    return Lote.objects.create(
        producto=producto,
        numero_lote='LOTE-TEST-002',
        fecha_caducidad='2026-12-31',
        cantidad_inicial=50,
        cantidad_actual=0,
        estado='agotado'
    )


@pytest.fixture
def centro(db):
    """Crea un centro de prueba."""
    return Centro.objects.create(
        clave='CENTRO01',
        nombre='Centro de Prueba',
        direccion='Dirección de prueba',
        activo=True
    )


@pytest.fixture
def usuario(db):
    """Crea un usuario de prueba."""
    return User.objects.create_user(
        username='test_stock_user',
        email='test@test.com',
        password='testpass123'
    )


class TestRegistrarMovimientoStockEntradas:
    """Tests para movimientos de tipo entrada."""

    def test_entrada_incrementa_stock(self, lote_con_stock):
        """Una entrada debe incrementar el stock del lote."""
        stock_inicial = lote_con_stock.cantidad_actual
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='entrada',
            cantidad=25,
            observaciones='Entrada de prueba'
        )
        
        assert lote_actualizado.cantidad_actual == stock_inicial + 25
        assert movimiento.tipo == 'entrada'
        assert movimiento.cantidad == 25
        assert movimiento.lote == lote_actualizado

    def test_entrada_con_cantidad_negativa_se_convierte_a_positiva(self, lote_con_stock):
        """Una entrada con cantidad negativa debe convertirse a positiva."""
        stock_inicial = lote_con_stock.cantidad_actual
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='entrada',
            cantidad=-10,
            observaciones='Entrada con signo negativo'
        )
        
        assert lote_actualizado.cantidad_actual == stock_inicial + 10
        assert movimiento.cantidad == 10

    def test_entrada_en_lote_agotado_reactiva_disponibilidad(self, lote_agotado):
        """Una entrada en lote agotado debe cambiar estado a disponible."""
        assert lote_agotado.estado == 'agotado'
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_agotado,
            tipo='entrada',
            cantidad=20,
            observaciones='Reabastecimiento'
        )
        
        assert lote_actualizado.cantidad_actual == 20
        assert lote_actualizado.estado == 'disponible'


class TestRegistrarMovimientoStockSalidas:
    """Tests para movimientos de tipo salida."""

    def test_salida_decrementa_stock(self, lote_con_stock):
        """Una salida debe decrementar el stock del lote."""
        stock_inicial = lote_con_stock.cantidad_actual
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='salida',
            cantidad=30,
            observaciones='Salida de prueba'
        )
        
        assert lote_actualizado.cantidad_actual == stock_inicial - 30
        assert movimiento.tipo == 'salida'
        assert movimiento.cantidad == -30  # Las salidas se guardan como negativas

    def test_salida_stock_insuficiente_lanza_error(self, lote_con_stock):
        """Una salida mayor al stock disponible debe lanzar error."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            registrar_movimiento_stock(
                lote=lote_con_stock,
                tipo='salida',
                cantidad=999,  # Mayor al stock disponible (100)
                observaciones='Intento de salida excesiva'
            )
        
        assert 'Stock insuficiente' in str(exc_info.value)

    def test_salida_total_agota_lote(self, lote_con_stock):
        """Una salida igual al stock debe agotar el lote."""
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='salida',
            cantidad=100,  # Todo el stock
            observaciones='Salida total'
        )
        
        assert lote_actualizado.cantidad_actual == 0
        assert lote_actualizado.estado == 'agotado'

    def test_salida_en_lote_agotado_lanza_error(self, lote_agotado):
        """Una salida en lote agotado debe lanzar error."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            registrar_movimiento_stock(
                lote=lote_agotado,
                tipo='salida',
                cantidad=1,
                observaciones='Intento salida en lote agotado'
            )
        
        assert 'Stock insuficiente' in str(exc_info.value)


class TestRegistrarMovimientoStockAjustes:
    """Tests para movimientos de tipo ajuste."""

    def test_ajuste_positivo_incrementa_stock(self, lote_con_stock):
        """Un ajuste positivo debe incrementar el stock (sin exceder inicial)."""
        # Primero hacer una salida para tener margen
        registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='salida',
            cantidad=50,
            observaciones='Crear margen para ajuste'
        )
        lote_con_stock.refresh_from_db()
        stock_antes = lote_con_stock.cantidad_actual  # 50
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='ajuste',
            cantidad=15,
            observaciones='Ajuste por inventario físico'
        )
        
        assert lote_actualizado.cantidad_actual == stock_antes + 15
        assert movimiento.tipo == 'ajuste'
        assert movimiento.cantidad == 15

    def test_ajuste_negativo_decrementa_stock(self, lote_con_stock):
        """Un ajuste negativo debe decrementar el stock."""
        stock_inicial = lote_con_stock.cantidad_actual
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='ajuste',
            cantidad=-20,
            observaciones='Ajuste por merma'
        )
        
        assert lote_actualizado.cantidad_actual == stock_inicial - 20
        assert movimiento.cantidad == -20


class TestRegistrarMovimientoStockValidaciones:
    """Tests para validaciones del helper."""

    def test_tipo_invalido_lanza_error(self, lote_con_stock):
        """Un tipo de movimiento no válido debe lanzar error."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            registrar_movimiento_stock(
                lote=lote_con_stock,
                tipo='invalido',
                cantidad=10,
                observaciones='Tipo inválido'
            )
        
        assert 'Tipo de movimiento no valido' in str(exc_info.value)

    def test_cantidad_nula_lanza_error(self, lote_con_stock):
        """Una cantidad nula debe lanzar error."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            registrar_movimiento_stock(
                lote=lote_con_stock,
                tipo='entrada',
                cantidad=None,
                observaciones='Cantidad nula'
            )
        
        assert 'Cantidad requerida' in str(exc_info.value)

    def test_cantidad_no_numerica_lanza_error(self, lote_con_stock):
        """Una cantidad no numérica debe lanzar error."""
        with pytest.raises(serializers.ValidationError) as exc_info:
            registrar_movimiento_stock(
                lote=lote_con_stock,
                tipo='entrada',
                cantidad='abc',
                observaciones='Cantidad no numérica'
            )
        
        assert 'numero entero' in str(exc_info.value)

    def test_tipo_case_insensitive(self, lote_con_stock):
        """El tipo debe ser case-insensitive."""
        stock_inicial = lote_con_stock.cantidad_actual
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='ENTRADA',  # Mayúsculas
            cantidad=5,
            observaciones='Test case insensitive'
        )
        
        assert lote_actualizado.cantidad_actual == stock_inicial + 5
        assert movimiento.tipo == 'entrada'  # Debe normalizarse a minúsculas


class TestRegistrarMovimientoStockConUsuarioYCentro:
    """Tests para movimientos con usuario y centro asociados."""

    def test_movimiento_con_usuario_autenticado(self, lote_con_stock, usuario):
        """Un movimiento con usuario autenticado debe guardar el usuario."""
        # Usuario creado con create_user ya está autenticado cuando tiene pk
        movimiento, _ = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='entrada',
            cantidad=10,
            usuario=usuario,
            observaciones='Con usuario'
        )
        
        assert movimiento.usuario == usuario

    def test_movimiento_con_centro(self, lote_con_stock, centro):
        """Un movimiento con centro debe guardarlo correctamente."""
        movimiento, _ = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='salida',
            cantidad=5,
            centro=centro,
            observaciones='Con centro'
        )
        
        assert movimiento.centro == centro

    def test_movimiento_sin_usuario_guarda_null(self, lote_con_stock):
        """Un movimiento sin usuario debe guardar null."""
        movimiento, _ = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='entrada',
            cantidad=10,
            usuario=None,
            observaciones='Sin usuario'
        )
        
        assert movimiento.usuario is None


class TestRegistrarMovimientoStockAtomicidad:
    """Tests para verificar atomicidad de las transacciones."""

    def test_error_no_deja_movimiento_huerfano(self, lote_con_stock):
        """Si falla la actualización, no debe quedar movimiento huérfano."""
        movimientos_antes = Movimiento.objects.count()
        stock_antes = lote_con_stock.cantidad_actual
        
        try:
            registrar_movimiento_stock(
                lote=lote_con_stock,
                tipo='salida',
                cantidad=999,  # Más del stock disponible
                observaciones='Debería fallar'
            )
        except serializers.ValidationError:
            pass
        
        # Verificar que no se creó movimiento ni cambió el stock
        assert Movimiento.objects.count() == movimientos_antes
        lote_con_stock.refresh_from_db()
        assert lote_con_stock.cantidad_actual == stock_antes
