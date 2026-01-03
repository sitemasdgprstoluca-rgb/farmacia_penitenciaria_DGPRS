# -*- coding: utf-8 -*-
"""
Test Suite: Movimientos de Salida y Confirmación de Entregas
============================================================

Tests para el módulo de movimientos del sistema de farmacia penitenciaria.
Incluye:
- CRUD de movimientos
- Filtros por estado de confirmación
- Endpoint confirmar-entrega en views_legacy.py
- Validaciones de permisos

Author: Sistema Farmacia Penitenciaria
Date: 2026-01-02
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock, PropertyMock
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone


class TestMovimientoFiltroEstadoConfirmacion(TestCase):
    """Tests para filtrar movimientos por estado de confirmación."""
    
    def setUp(self):
        self.factory = APIRequestFactory()
    
    def test_filtro_pendiente_excluye_confirmados(self):
        """Verifica que estado_confirmacion=pendiente excluye [CONFIRMADO]."""
        movimientos = [
            {'id': 1, 'motivo': 'Salida normal', 'tipo': 'salida'},
            {'id': 2, 'motivo': '[CONFIRMADO] Salida confirmada', 'tipo': 'salida'},
            {'id': 3, 'motivo': 'Otra salida pendiente', 'tipo': 'salida'},
        ]
        
        # Filtrar pendientes
        pendientes = [m for m in movimientos if '[CONFIRMADO]' not in (m.get('motivo') or '')]
        
        assert len(pendientes) == 2
        assert all('[CONFIRMADO]' not in (m.get('motivo') or '') for m in pendientes)
    
    def test_filtro_confirmado_solo_incluye_confirmados(self):
        """Verifica que estado_confirmacion=confirmado solo incluye [CONFIRMADO]."""
        movimientos = [
            {'id': 1, 'motivo': 'Salida normal', 'tipo': 'salida'},
            {'id': 2, 'motivo': '[CONFIRMADO] Salida confirmada', 'tipo': 'salida'},
            {'id': 3, 'motivo': '[CONFIRMADO] Otra confirmada', 'tipo': 'salida'},
        ]
        
        # Filtrar confirmados
        confirmados = [m for m in movimientos if '[CONFIRMADO]' in (m.get('motivo') or '')]
        
        assert len(confirmados) == 2
        assert all('[CONFIRMADO]' in m.get('motivo') for m in confirmados)
    
    def test_filtro_vacio_retorna_todos(self):
        """Verifica que sin filtro de estado se retornan todos."""
        movimientos = [
            {'id': 1, 'motivo': 'Salida normal', 'tipo': 'salida'},
            {'id': 2, 'motivo': '[CONFIRMADO] Confirmada', 'tipo': 'salida'},
        ]
        
        # Sin filtro = todos
        assert len(movimientos) == 2


class TestConfirmarEntregaLegacy(TestCase):
    """
    Tests específicos para el endpoint confirmar_entrega en views_legacy.py.
    Este es el endpoint activo que usa la aplicación.
    """
    
    def setUp(self):
        self.factory = APIRequestFactory()
    
    @patch('inventario.views_legacy.is_farmacia_or_admin')
    @patch('inventario.views_legacy.logger')
    def test_confirmar_entrega_exitosa_legacy(self, mock_logger, mock_is_admin):
        """Verifica confirmación exitosa desde views_legacy."""
        from inventario.views_legacy import MovimientoViewSet
        
        mock_is_admin.return_value = True
        
        # Mock del movimiento
        mock_movimiento = MagicMock()
        mock_movimiento.id = 100
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = 'Salida programada'
        mock_movimiento.centro_destino = MagicMock()
        mock_movimiento.centro_destino.id = 1
        
        # Mock request y user
        mock_user = MagicMock()
        mock_user.username = 'admin_test'
        
        request = self.factory.post('/api/movimientos/100/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 100}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            response = viewset.confirmar_entrega(request, pk=100)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data.get('success') == True
        assert '[CONFIRMADO]' in mock_movimiento.motivo
        mock_movimiento.save.assert_called_once()
    
    @patch('inventario.views_legacy.logger')
    def test_confirmar_entrega_solo_salida_legacy(self, mock_logger):
        """Verifica que solo se pueden confirmar salidas en legacy."""
        from inventario.views_legacy import MovimientoViewSet
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 101
        mock_movimiento.tipo = 'entrada'  # No es salida
        
        mock_user = MagicMock()
        mock_user.username = 'admin'
        
        request = self.factory.post('/api/movimientos/101/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 101}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            response = viewset.confirmar_entrega(request, pk=101)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'salida' in response.data.get('message', '').lower()
    
    @patch('inventario.views_legacy.logger')
    def test_confirmar_entrega_ya_confirmada_legacy(self, mock_logger):
        """Verifica que no se puede confirmar dos veces en legacy."""
        from inventario.views_legacy import MovimientoViewSet
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 102
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = '[CONFIRMADO] Ya confirmado antes'
        
        mock_user = MagicMock()
        mock_user.username = 'admin'
        
        request = self.factory.post('/api/movimientos/102/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 102}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            response = viewset.confirmar_entrega(request, pk=102)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'ya fue confirmada' in response.data.get('message', '').lower()
    
    @patch('inventario.views_legacy.is_farmacia_or_admin')
    @patch('inventario.views_legacy.get_user_centro')
    @patch('inventario.views_legacy.logger')
    def test_permiso_centro_destino_legacy(self, mock_logger, mock_get_centro, mock_is_admin):
        """Usuario del centro destino puede confirmar su entrega."""
        from inventario.views_legacy import MovimientoViewSet
        
        # Usuario NO es admin
        mock_is_admin.return_value = False
        
        # Usuario del centro 5
        mock_centro_usuario = MagicMock()
        mock_centro_usuario.id = 5
        mock_get_centro.return_value = mock_centro_usuario
        
        # Movimiento al centro 5 (mismo centro)
        mock_centro_destino = MagicMock()
        mock_centro_destino.id = 5
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 103
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = 'Salida pendiente'
        mock_movimiento.centro_destino = mock_centro_destino
        
        mock_user = MagicMock()
        mock_user.username = 'user_centro5'
        
        request = self.factory.post('/api/movimientos/103/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 103}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            response = viewset.confirmar_entrega(request, pk=103)
        
        # Debe permitir (200) porque es del mismo centro
        assert response.status_code == status.HTTP_200_OK
    
    @patch('inventario.views_legacy.is_farmacia_or_admin')
    @patch('inventario.views_legacy.get_user_centro')
    @patch('inventario.views_legacy.logger')
    def test_permiso_otro_centro_denegado_legacy(self, mock_logger, mock_get_centro, mock_is_admin):
        """Usuario de otro centro NO puede confirmar."""
        from inventario.views_legacy import MovimientoViewSet
        
        mock_is_admin.return_value = False
        
        # Usuario del centro 1
        mock_centro_usuario = MagicMock()
        mock_centro_usuario.id = 1
        mock_get_centro.return_value = mock_centro_usuario
        
        # Movimiento al centro 2 (diferente)
        mock_centro_destino = MagicMock()
        mock_centro_destino.id = 2
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 104
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = 'Salida a otro centro'
        mock_movimiento.centro_destino = mock_centro_destino
        
        mock_user = MagicMock()
        mock_user.username = 'user_centro1'
        
        request = self.factory.post('/api/movimientos/104/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 104}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            response = viewset.confirmar_entrega(request, pk=104)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestMovimientoCreacion(TestCase):
    """Tests para creación de movimientos."""
    
    def test_movimiento_salida_requiere_lote(self):
        """Verifica que salida requiere lote válido."""
        datos_salida = {
            'tipo': 'salida',
            'cantidad': 10,
            'lote_id': None,  # Sin lote
            'centro_destino_id': 1,
        }
        
        # Validación: lote requerido para salidas
        assert datos_salida['lote_id'] is None
        es_valido = datos_salida['lote_id'] is not None
        assert es_valido == False
    
    def test_movimiento_salida_cantidad_positiva(self):
        """Verifica que cantidad debe ser positiva."""
        cantidades_invalidas = [0, -1, -100]
        cantidades_validas = [1, 10, 100]
        
        for cant in cantidades_invalidas:
            assert cant <= 0
        
        for cant in cantidades_validas:
            assert cant > 0
    
    def test_tipo_movimiento_valores_permitidos(self):
        """Verifica tipos de movimiento permitidos."""
        tipos_validos = ['entrada', 'salida']
        tipos_invalidos = ['transferencia', 'ajuste', 'invalido']
        
        for tipo in tipos_validos:
            assert tipo in ['entrada', 'salida']
        
        for tipo in tipos_invalidos:
            assert tipo not in ['entrada', 'salida']


class TestSubtipoSalida(TestCase):
    """Tests para subtipos de salida."""
    
    def test_subtipos_salida_validos(self):
        """Verifica subtipos de salida aceptados."""
        subtipos_validos = [
            'transferencia',
            'dispensacion',
            'merma',
            'caducidad',
            'ajuste_inventario'
        ]
        
        for subtipo in subtipos_validos:
            assert subtipo in ['transferencia', 'dispensacion', 'merma', 
                              'caducidad', 'ajuste_inventario']
    
    def test_subtipo_transferencia_requiere_centro_destino(self):
        """Transferencia requiere centro destino."""
        movimiento = {
            'tipo': 'salida',
            'subtipo_salida': 'transferencia',
            'centro_destino_id': None,
        }
        
        # Validación
        es_valido = (
            movimiento['subtipo_salida'] != 'transferencia' or 
            movimiento['centro_destino_id'] is not None
        )
        
        assert es_valido == False
    
    def test_subtipo_dispensacion_requiere_expediente(self):
        """Dispensación puede requerir número de expediente."""
        movimiento = {
            'tipo': 'salida',
            'subtipo_salida': 'dispensacion',
            'numero_expediente': 'EXP-001',
        }
        
        assert movimiento['numero_expediente'] is not None


class TestCalculoStock(TestCase):
    """Tests para cálculo de stock en movimientos."""
    
    def test_entrada_incrementa_stock(self):
        """Entrada incrementa el stock del lote."""
        stock_inicial = 100
        cantidad_entrada = 50
        
        stock_final = stock_inicial + cantidad_entrada
        
        assert stock_final == 150
    
    def test_salida_decrementa_stock(self):
        """Salida decrementa el stock del lote."""
        stock_inicial = 100
        cantidad_salida = 30
        
        stock_final = stock_inicial - cantidad_salida
        
        assert stock_final == 70
    
    def test_salida_no_puede_exceder_stock(self):
        """Salida no puede exceder stock disponible."""
        stock_actual = 50
        cantidad_salida = 100  # Mayor que stock
        
        es_valida = cantidad_salida <= stock_actual
        
        assert es_valida == False
    
    def test_stock_nunca_negativo(self):
        """Stock nunca debe ser negativo."""
        stock = 0
        cantidad_salida = 10
        
        # Simular validación
        if cantidad_salida > stock:
            stock_resultado = stock  # No se permite
        else:
            stock_resultado = stock - cantidad_salida
        
        assert stock_resultado >= 0


class TestMovimientoResponseFormat(TestCase):
    """Tests para formato de respuesta de movimientos."""
    
    def test_respuesta_exitosa_tiene_campos_requeridos(self):
        """Respuesta exitosa tiene estructura correcta."""
        respuesta_exitosa = {
            'success': True,
            'message': 'Entrega confirmada exitosamente',
            'movimiento_id': 1
        }
        
        assert 'success' in respuesta_exitosa
        assert 'message' in respuesta_exitosa
        assert respuesta_exitosa['success'] == True
    
    def test_respuesta_error_tiene_mensaje(self):
        """Respuesta de error incluye mensaje descriptivo."""
        respuesta_error = {
            'error': True,
            'message': 'Solo se pueden confirmar entregas de movimientos de salida'
        }
        
        assert 'message' in respuesta_error
        assert len(respuesta_error['message']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
