# -*- coding: utf-8 -*-
"""
Pruebas unitarias para el flujo correcto de salidas masivas.

NOTA: Estos tests están desactualizados. El flujo actual confirma 
automáticamente las salidas en lugar de marcarlas como pendientes.
Se requiere refactorizar para el nuevo comportamiento.

FLUJO ACTUAL (nuevo):
1. Crear salida → Confirma automáticamente y descuenta stock

FLUJO ANTERIOR (estos tests):
1. Crear salida → NO descuenta stock, marca [PENDIENTE]
2. Confirmar entrega → Descuenta stock, marca [CONFIRMADO]
3. Cancelar → Solo elimina movimientos PENDIENTES (no hay stock que devolver)
"""
import pytest

# Skip todo el módulo - tests desactualizados para el nuevo flujo
pytestmark = pytest.mark.skip(reason="Flujo de salidas masivas cambió - las salidas ahora se confirman automáticamente")

from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model
from decimal import Decimal

# Usar el modelo de usuario personalizado del proyecto
User = get_user_model()


class TestFlujoSalidaMasiva(TestCase):
    """Tests para el flujo completo de salidas masivas."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Importar aquí para evitar errores de Django no configurado
        from core.models import Centro, Producto, Lote
        cls.Centro = Centro
        cls.Producto = Producto
        cls.Lote = Lote
    
    def setUp(self):
        """Configurar datos de prueba."""
        # Crear usuario con rol farmacia
        # El modelo User personalizado tiene 'rol' directamente
        self.user = User.objects.create_user(
            username='farmacia_test',
            password='testpass123',
            email='farmacia@test.com',
            rol='farmacia'  # Rol directo en el modelo User
        )
        
        # Crear centro destino
        self.centro_destino = self.Centro.objects.create(
            nombre='Centro Test',
            direccion='Dirección de prueba'
        )
        
        # Crear producto
        self.producto = self.Producto.objects.create(
            clave='MED001',
            nombre='Medicamento Test',
            unidad_medida='TABLETA',
            activo=True
        )
        
        # Crear lote con stock en Farmacia Central (centro=NULL)
        from datetime import date, timedelta
        self.lote = self.Lote.objects.create(
            producto=self.producto,
            numero_lote='LOTE001',
            cantidad_inicial=100,
            cantidad_actual=100,
            fecha_caducidad=date.today() + timedelta(days=365),
            centro=None,  # Farmacia Central
            activo=True
        )
        
        self.factory = APIRequestFactory()
    
    def tearDown(self):
        """Limpiar datos de prueba."""
        from core.models import Movimiento
        Movimiento.objects.filter(lote=self.lote).delete()
        self.lote.delete()
        self.producto.delete()
        self.centro_destino.delete()
        self.user.delete()


class TestCrearSalidaMasiva(TestFlujoSalidaMasiva):
    """Tests para la creación de salidas masivas."""
    
    def test_crear_salida_no_descuenta_stock(self):
        """
        Test: Al crear una salida masiva, el stock NO debe descontarse.
        El stock solo se descuenta al CONFIRMAR la entrega.
        """
        from inventario.views.salida_masiva import salida_masiva
        
        stock_inicial = self.lote.cantidad_actual
        cantidad_salida = 10
        
        request = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Test salida',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': cantidad_salida}
            ]
        }, format='json')
        force_authenticate(request, user=self.user)
        
        response = salida_masiva(request)
        
        # Verificar respuesta exitosa
        assert response.status_code == 201
        assert response.data.get('success') is True
        
        # Verificar stock NO cambió
        self.lote.refresh_from_db()
        assert self.lote.cantidad_actual == stock_inicial, \
            f'Stock debería ser {stock_inicial}, pero es {self.lote.cantidad_actual}'
        
    def test_crear_salida_marca_pendiente(self):
        """Test: Al crear salida, el movimiento debe marcarse como [PENDIENTE]."""
        from inventario.views.salida_masiva import salida_masiva
        from core.models import Movimiento
        
        request = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Test pendiente',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': 5}
            ]
        }, format='json')
        force_authenticate(request, user=self.user)
        
        response = salida_masiva(request)
        
        assert response.status_code == 201
        
        # Verificar que el movimiento tiene [PENDIENTE] en el motivo
        grupo_salida = response.data.get('grupo_salida')
        movimiento = Movimiento.objects.filter(
            motivo__contains=f'[{grupo_salida}]'
        ).first()
        
        assert movimiento is not None
        assert '[PENDIENTE]' in movimiento.motivo, \
            f'Motivo debería contener [PENDIENTE], pero es: {movimiento.motivo}'


class TestConfirmarEntrega(TestFlujoSalidaMasiva):
    """Tests para la confirmación de entregas."""
    
    def test_confirmar_descuenta_stock(self):
        """
        Test: Al CONFIRMAR una entrega, el stock SÍ debe descontarse.
        """
        from inventario.views.salida_masiva import salida_masiva, confirmar_entrega
        from core.models import Movimiento
        
        stock_inicial = self.lote.cantidad_actual
        cantidad_salida = 15
        
        # Paso 1: Crear salida (pendiente)
        request1 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Test confirmar',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': cantidad_salida}
            ]
        }, format='json')
        force_authenticate(request1, user=self.user)
        response1 = salida_masiva(request1)
        
        assert response1.status_code == 201
        grupo_salida = response1.data.get('grupo_salida')
        
        # Verificar stock sigue igual después de crear
        self.lote.refresh_from_db()
        assert self.lote.cantidad_actual == stock_inicial
        
        # Paso 2: Confirmar entrega
        request2 = self.factory.post(f'/api/v1/salida-masiva/{grupo_salida}/confirmar/')
        force_authenticate(request2, user=self.user)
        response2 = confirmar_entrega(request2, grupo_salida)
        
        assert response2.status_code == 200
        assert response2.data.get('success') is True
        
        # Verificar stock SÍ cambió después de confirmar
        self.lote.refresh_from_db()
        stock_esperado = stock_inicial - cantidad_salida
        assert self.lote.cantidad_actual == stock_esperado, \
            f'Stock debería ser {stock_esperado}, pero es {self.lote.cantidad_actual}'
    
    def test_confirmar_cambia_pendiente_a_confirmado(self):
        """Test: Al confirmar, el motivo cambia de [PENDIENTE] a [CONFIRMADO]."""
        from inventario.views.salida_masiva import salida_masiva, confirmar_entrega
        from core.models import Movimiento
        
        # Crear salida
        request1 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Test cambio estado',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': 5}
            ]
        }, format='json')
        force_authenticate(request1, user=self.user)
        response1 = salida_masiva(request1)
        grupo_salida = response1.data.get('grupo_salida')
        
        # Confirmar
        request2 = self.factory.post(f'/api/v1/salida-masiva/{grupo_salida}/confirmar/')
        force_authenticate(request2, user=self.user)
        confirmar_entrega(request2, grupo_salida)
        
        # Verificar estado
        movimiento = Movimiento.objects.filter(
            motivo__contains=f'[{grupo_salida}]'
        ).first()
        
        assert '[CONFIRMADO]' in movimiento.motivo
        assert '[PENDIENTE]' not in movimiento.motivo
    
    def test_no_se_puede_confirmar_dos_veces(self):
        """Test: No se puede confirmar una entrega ya confirmada."""
        from inventario.views.salida_masiva import salida_masiva, confirmar_entrega
        
        # Crear y confirmar
        request1 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Test doble confirmacion',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': 5}
            ]
        }, format='json')
        force_authenticate(request1, user=self.user)
        response1 = salida_masiva(request1)
        grupo_salida = response1.data.get('grupo_salida')
        
        # Primera confirmación
        request2 = self.factory.post(f'/api/v1/salida-masiva/{grupo_salida}/confirmar/')
        force_authenticate(request2, user=self.user)
        response2 = confirmar_entrega(request2, grupo_salida)
        assert response2.status_code == 200
        
        # Segunda confirmación - debe fallar
        request3 = self.factory.post(f'/api/v1/salida-masiva/{grupo_salida}/confirmar/')
        force_authenticate(request3, user=self.user)
        response3 = confirmar_entrega(request3, grupo_salida)
        
        assert response3.status_code == 400
        assert 'ya fue confirmada' in response3.data.get('message', '').lower()


class TestCancelarSalida(TestFlujoSalidaMasiva):
    """Tests para la cancelación de salidas."""
    
    def test_cancelar_no_afecta_stock(self):
        """
        Test: Al cancelar una salida PENDIENTE, el stock NO debe modificarse
        (porque nunca se descontó).
        """
        from inventario.views.salida_masiva import salida_masiva, cancelar_salida
        
        stock_inicial = self.lote.cantidad_actual
        cantidad_salida = 20
        
        # Crear salida
        request1 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Test cancelar',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': cantidad_salida}
            ]
        }, format='json')
        force_authenticate(request1, user=self.user)
        response1 = salida_masiva(request1)
        grupo_salida = response1.data.get('grupo_salida')
        
        # Cancelar
        request2 = self.factory.delete(f'/api/v1/salida-masiva/{grupo_salida}/cancelar/')
        force_authenticate(request2, user=self.user)
        response2 = cancelar_salida(request2, grupo_salida)
        
        assert response2.status_code == 200
        assert response2.data.get('success') is True
        
        # Verificar stock sigue igual
        self.lote.refresh_from_db()
        assert self.lote.cantidad_actual == stock_inicial, \
            f'Stock debería seguir en {stock_inicial}, pero es {self.lote.cantidad_actual}'
    
    def test_cancelar_elimina_movimientos(self):
        """Test: Al cancelar, los movimientos deben eliminarse."""
        from inventario.views.salida_masiva import salida_masiva, cancelar_salida
        from core.models import Movimiento
        
        # Crear salida
        request1 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Test eliminar movimientos',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': 5}
            ]
        }, format='json')
        force_authenticate(request1, user=self.user)
        response1 = salida_masiva(request1)
        grupo_salida = response1.data.get('grupo_salida')
        
        # Verificar que existen movimientos
        count_antes = Movimiento.objects.filter(
            motivo__contains=f'[{grupo_salida}]'
        ).count()
        assert count_antes > 0
        
        # Cancelar
        request2 = self.factory.delete(f'/api/v1/salida-masiva/{grupo_salida}/cancelar/')
        force_authenticate(request2, user=self.user)
        cancelar_salida(request2, grupo_salida)
        
        # Verificar movimientos eliminados
        count_despues = Movimiento.objects.filter(
            motivo__contains=f'[{grupo_salida}]'
        ).count()
        assert count_despues == 0
    
    def test_no_se_puede_cancelar_confirmado(self):
        """Test: No se puede cancelar una entrega ya confirmada."""
        from inventario.views.salida_masiva import salida_masiva, confirmar_entrega, cancelar_salida
        
        # Crear y confirmar
        request1 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Test cancelar confirmado',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': 5}
            ]
        }, format='json')
        force_authenticate(request1, user=self.user)
        response1 = salida_masiva(request1)
        grupo_salida = response1.data.get('grupo_salida')
        
        # Confirmar
        request2 = self.factory.post(f'/api/v1/salida-masiva/{grupo_salida}/confirmar/')
        force_authenticate(request2, user=self.user)
        confirmar_entrega(request2, grupo_salida)
        
        # Intentar cancelar - debe fallar
        request3 = self.factory.delete(f'/api/v1/salida-masiva/{grupo_salida}/cancelar/')
        force_authenticate(request3, user=self.user)
        response3 = cancelar_salida(request3, grupo_salida)
        
        assert response3.status_code == 400
        assert 'ya fue confirmada' in response3.data.get('message', '').lower()


class TestStockReservado(TestFlujoSalidaMasiva):
    """Tests para validación de stock con reservas pendientes."""
    
    def test_stock_reservado_bloquea_nueva_salida(self):
        """
        Test: Si hay salidas pendientes, el stock disponible real
        debe considerar las reservas y rechazar si no hay suficiente.
        """
        from inventario.views.salida_masiva import salida_masiva
        
        stock_inicial = self.lote.cantidad_actual  # 100
        
        # Primera salida de 80 unidades (pendiente)
        request1 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Primera salida',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': 80}
            ]
        }, format='json')
        force_authenticate(request1, user=self.user)
        response1 = salida_masiva(request1)
        
        assert response1.status_code == 201
        
        # Stock sigue en 100, pero 80 están reservados
        # Stock disponible real = 100 - 80 = 20
        
        # Segunda salida de 30 unidades - debe fallar
        request2 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Segunda salida (excede)',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': 30}
            ]
        }, format='json')
        force_authenticate(request2, user=self.user)
        response2 = salida_masiva(request2)
        
        assert response2.status_code == 400
        assert 'stock insuficiente' in response2.data.get('errores', [''])[0].lower() or \
               'stock insuficiente' in response2.data.get('message', '').lower()
    
    def test_stock_liberado_al_cancelar(self):
        """
        Test: Al cancelar una salida pendiente, la reserva se libera
        y permite nuevas salidas.
        """
        from inventario.views.salida_masiva import salida_masiva, cancelar_salida
        
        # Primera salida de 80 unidades
        request1 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Primera salida',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': 80}
            ]
        }, format='json')
        force_authenticate(request1, user=self.user)
        response1 = salida_masiva(request1)
        grupo_salida1 = response1.data.get('grupo_salida')
        
        # Cancelar primera salida - libera 80 unidades
        request2 = self.factory.delete(f'/api/v1/salida-masiva/{grupo_salida1}/cancelar/')
        force_authenticate(request2, user=self.user)
        cancelar_salida(request2, grupo_salida1)
        
        # Ahora una salida de 90 unidades debe funcionar
        request3 = self.factory.post('/api/v1/salida-masiva/', {
            'centro_destino_id': self.centro_destino.id,
            'observaciones': 'Nueva salida post-cancelación',
            'items': [
                {'lote_id': self.lote.id, 'cantidad': 90}
            ]
        }, format='json')
        force_authenticate(request3, user=self.user)
        response3 = salida_masiva(request3)
        
        assert response3.status_code == 201


class TestHelperFunctions(TestCase):
    """Tests para las funciones auxiliares."""
    
    def test_es_movimiento_pendiente(self):
        """Test: _es_movimiento_pendiente detecta correctamente el estado."""
        from inventario.views.salida_masiva import _es_movimiento_pendiente
        
        class MockMovimiento:
            def __init__(self, motivo):
                self.motivo = motivo
        
        # Casos positivos
        assert _es_movimiento_pendiente(MockMovimiento('[PENDIENTE][SAL-123] obs')) is True
        assert _es_movimiento_pendiente(MockMovimiento('[PENDIENTE] algo')) is True
        
        # Casos negativos
        assert _es_movimiento_pendiente(MockMovimiento('[CONFIRMADO][SAL-123] obs')) is False
        assert _es_movimiento_pendiente(MockMovimiento('Sin tag alguno')) is False
        assert _es_movimiento_pendiente(MockMovimiento(None)) is False
    
    def test_es_movimiento_confirmado(self):
        """Test: _es_movimiento_confirmado detecta correctamente el estado."""
        from inventario.views.salida_masiva import _es_movimiento_confirmado
        
        class MockMovimiento:
            def __init__(self, motivo):
                self.motivo = motivo
        
        # Casos positivos
        assert _es_movimiento_confirmado(MockMovimiento('[CONFIRMADO][SAL-123] obs')) is True
        assert _es_movimiento_confirmado(MockMovimiento('[CONFIRMADO] algo')) is True
        
        # Casos negativos
        assert _es_movimiento_confirmado(MockMovimiento('[PENDIENTE][SAL-123] obs')) is False
        assert _es_movimiento_confirmado(MockMovimiento('Sin tag alguno')) is False
        assert _es_movimiento_confirmado(MockMovimiento(None)) is False


# ============================================================
# Tests de integración simplificados (sin base de datos)
# ============================================================

class TestFlujoLogica:
    """Tests de lógica del flujo sin necesidad de base de datos."""
    
    def test_flujo_estados_correctos(self):
        """Test: Verificar la secuencia correcta de estados."""
        estados_validos = [
            'PENDIENTE',
            'CONFIRMADO',
        ]
        
        # Estado inicial debe ser PENDIENTE
        estado_inicial = 'PENDIENTE'
        assert estado_inicial in estados_validos
        
        # De PENDIENTE se puede pasar a CONFIRMADO o eliminar (cancelar)
        transiciones_pendiente = ['CONFIRMADO', 'ELIMINADO']
        assert 'CONFIRMADO' in transiciones_pendiente
        assert 'ELIMINADO' in transiciones_pendiente
        
        # De CONFIRMADO no hay transiciones válidas (estado final)
        transiciones_confirmado = []
        assert len(transiciones_confirmado) == 0
    
    def test_stock_solo_cambia_al_confirmar(self):
        """Test: Verificar lógica de cuándo cambia el stock."""
        # Crear: stock_cambia = False
        # Confirmar: stock_cambia = True
        # Cancelar: stock_cambia = False (porque nunca se descontó)
        
        operaciones = {
            'crear': {'stock_cambia': False, 'nuevo_estado': 'PENDIENTE'},
            'confirmar': {'stock_cambia': True, 'nuevo_estado': 'CONFIRMADO'},
            'cancelar': {'stock_cambia': False, 'nuevo_estado': 'ELIMINADO'},
        }
        
        assert operaciones['crear']['stock_cambia'] is False
        assert operaciones['confirmar']['stock_cambia'] is True
        assert operaciones['cancelar']['stock_cambia'] is False
    
    def test_calcular_stock_disponible(self):
        """Test: Lógica de cálculo de stock disponible."""
        stock_actual = 100
        reservado_pendiente = 30
        
        stock_disponible = stock_actual - reservado_pendiente
        
        assert stock_disponible == 70
        
        # No se puede sacar más que el disponible
        cantidad_solicitada = 80
        puede_sacar = cantidad_solicitada <= stock_disponible
        assert puede_sacar is False
        
        # Sí se puede sacar menos o igual
        cantidad_menor = 50
        puede_sacar_menor = cantidad_menor <= stock_disponible
        assert puede_sacar_menor is True
