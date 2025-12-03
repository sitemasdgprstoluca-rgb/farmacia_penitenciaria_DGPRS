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


# ============================================================================
# ISS-002: TESTS DE VALIDACIÓN DE PERTENENCIA DE CENTRO
# ============================================================================

@pytest.fixture
def centro_a(db):
    """Centro A para tests de pertenencia."""
    return Centro.objects.create(
        clave='CENTRO_A',
        nombre='Centro A',
        direccion='Dirección A',
        activo=True
    )


@pytest.fixture
def centro_b(db):
    """Centro B para tests de pertenencia."""
    return Centro.objects.create(
        clave='CENTRO_B',
        nombre='Centro B',
        direccion='Dirección B',
        activo=True
    )


@pytest.fixture
def lote_farmacia_central(db, producto):
    """
    Lote de farmacia central (centro=None).
    Necesario como lote_origen para lotes en centros.
    """
    return Lote.objects.create(
        producto=producto,
        numero_lote='LOTE-CENTRAL',
        fecha_caducidad='2026-12-31',
        cantidad_inicial=500,
        cantidad_actual=500,
        estado='disponible',
        centro=None,  # Farmacia central
        lote_origen=None
    )


@pytest.fixture
def lote_centro_a(db, producto, centro_a, lote_farmacia_central):
    """
    Lote que pertenece al Centro A.
    Debe tener lote_origen de farmacia central para cumplir reglas de trazabilidad.
    """
    return Lote.objects.create(
        producto=producto,
        numero_lote='LOTE-CENTRAL',  # Debe coincidir con lote_origen
        fecha_caducidad='2026-12-31',  # Debe coincidir con lote_origen
        cantidad_inicial=100,
        cantidad_actual=100,
        estado='disponible',
        centro=centro_a,
        lote_origen=lote_farmacia_central
    )


@pytest.fixture
def usuario_centro_a(db, centro_a):
    """Usuario asignado al Centro A (rol centro, no admin)."""
    user = User.objects.create_user(
        username='user_centro_a',
        email='centro_a@test.com',
        password='testpass123'
    )
    user.rol = 'centro'
    user.centro = centro_a
    user.save()
    return user


@pytest.fixture
def usuario_farmacia(db):
    """Usuario con rol farmacia (acceso global)."""
    user = User.objects.create_user(
        username='user_farmacia',
        email='farmacia@test.com',
        password='testpass123'
    )
    user.rol = 'farmacia'
    user.save()
    return user


class TestRegistrarMovimientoStockPertenenciaCentro:
    """
    ISS-002: Tests para validación de pertenencia de centro.
    
    Verifica que usuarios de un centro no puedan manipular stock de otros centros.
    """

    def test_lote_centro_diferente_al_especificado_rechazado(self, lote_centro_a, centro_b):
        """
        ISS-002: Si el lote pertenece al Centro A pero se especifica Centro B,
        debe rechazarse la operación.
        """
        with pytest.raises(serializers.ValidationError) as exc_info:
            registrar_movimiento_stock(
                lote=lote_centro_a,  # Pertenece a Centro A
                tipo='salida',
                cantidad=10,
                centro=centro_b,  # Se intenta operar como Centro B
                observaciones='Intento de manipulación entre centros'
            )
        
        assert 'no pertenece al centro' in str(exc_info.value).lower()

    def test_lote_mismo_centro_aceptado(self, lote_centro_a, centro_a):
        """Centro correcto debe ser aceptado."""
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_centro_a,
            tipo='salida',
            cantidad=10,
            centro=centro_a,  # Centro correcto
            observaciones='Operación válida mismo centro'
        )
        
        assert lote_actualizado.cantidad_actual == 90
        assert movimiento.centro == centro_a

    def test_usuario_centro_diferente_rechazado(self, lote_centro_a, centro_b, db):
        """
        ISS-002: Usuario de Centro B no puede operar sobre lotes de Centro A.
        """
        # Crear usuario del Centro B
        user_centro_b = User.objects.create_user(
            username='user_centro_b_test',
            email='centro_b_test@test.com',
            password='testpass123'
        )
        user_centro_b.rol = 'centro'
        user_centro_b.centro = centro_b
        user_centro_b.save()
        
        with pytest.raises(serializers.ValidationError) as exc_info:
            registrar_movimiento_stock(
                lote=lote_centro_a,  # Pertenece a Centro A
                tipo='salida',
                cantidad=5,
                usuario=user_centro_b,  # Usuario de Centro B
                observaciones='Intento de acceso cruzado'
            )
        
        assert 'permiso' in str(exc_info.value).lower() or 'no pertenece' in str(exc_info.value).lower()

    def test_usuario_mismo_centro_aceptado(self, lote_centro_a, usuario_centro_a):
        """Usuario del mismo centro puede operar sobre sus lotes."""
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_centro_a,
            tipo='entrada',
            cantidad=20,
            usuario=usuario_centro_a,
            observaciones='Operación válida usuario mismo centro'
        )
        
        assert lote_actualizado.cantidad_actual == 120
        assert movimiento.usuario == usuario_centro_a

    def test_usuario_farmacia_puede_operar_cualquier_centro(self, lote_centro_a, usuario_farmacia, centro_b):
        """
        Usuarios con rol farmacia tienen acceso global y pueden operar
        sobre lotes de cualquier centro.
        """
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_centro_a,
            tipo='salida',
            cantidad=15,
            usuario=usuario_farmacia,
            centro=centro_b,  # Centro diferente al del lote
            skip_centro_check=True,  # Farmacia puede saltar la validación
            observaciones='Operación farmacia global'
        )
        
        assert lote_actualizado.cantidad_actual == 85

    def test_skip_centro_check_permite_operacion(self, lote_centro_a, centro_b):
        """
        Con skip_centro_check=True, se puede operar sin validar pertenencia.
        Útil para operaciones de sistema/admin.
        """
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_centro_a,
            tipo='ajuste',
            cantidad=-5,
            centro=centro_b,
            skip_centro_check=True,
            observaciones='Ajuste administrativo'
        )
        
        assert lote_actualizado.cantidad_actual == 95

    def test_lote_sin_centro_acepta_cualquier_centro(self, lote_con_stock, centro_a):
        """
        Si el lote no tiene centro asignado (lote.centro = None),
        cualquier centro puede operarlo.
        """
        # lote_con_stock no tiene centro asignado por defecto
        assert getattr(lote_con_stock, 'centro', None) is None
        
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_con_stock,
            tipo='entrada',
            cantidad=10,
            centro=centro_a,
            observaciones='Operación en lote sin centro'
        )
        
        assert lote_actualizado.cantidad_actual == 110

    def test_centro_none_no_valida_pertenencia(self, lote_centro_a):
        """
        Si no se especifica centro (centro=None), no se valida pertenencia.
        El movimiento se crea sin centro asociado.
        """
        movimiento, lote_actualizado = registrar_movimiento_stock(
            lote=lote_centro_a,
            tipo='salida',
            cantidad=5,
            centro=None,  # Sin centro específico
            observaciones='Salida sin centro'
        )
        
        assert lote_actualizado.cantidad_actual == 95
        assert movimiento.centro is None

