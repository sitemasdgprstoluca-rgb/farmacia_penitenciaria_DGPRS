"""
Tests unitarios para confirmar entrega de movimientos de salida individual.
Verifica el endpoint POST /api/movimientos/{id}/confirmar-entrega/
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from rest_framework import status
from unittest.mock import patch, MagicMock, PropertyMock


class TestConfirmarEntregaLogica(TestCase):
    """Tests para la lógica del endpoint confirmar-entrega."""
    
    def setUp(self):
        self.factory = APIRequestFactory()
    
    @patch('inventario.views.movimientos.logger')
    def test_confirmar_entrega_exitosa(self, mock_logger):
        """Verifica la lógica de confirmar entrega exitosa."""
        from inventario.views.movimientos import MovimientoViewSet
        
        # Mock del movimiento
        mock_movimiento = MagicMock()
        mock_movimiento.id = 1
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = 'Salida de prueba'
        mock_movimiento.centro_destino = MagicMock()
        mock_movimiento.centro_destino.id = 1
        
        # Mock del usuario
        mock_user = MagicMock()
        mock_user.username = 'admin_test'
        
        # Mock request
        request = self.factory.post('/api/movimientos/1/confirmar-entrega/')
        request.user = mock_user
        
        # Crear viewset y asignar mocks
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 1}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            with patch('inventario.views.movimientos.is_farmacia_or_admin', return_value=True):
                response = viewset.confirmar_entrega(request, pk=1)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] == True
        assert 'confirmada' in response.data['message'].lower()
        
        # Verificar que se llamó save
        mock_movimiento.save.assert_called_once()
        assert '[CONFIRMADO]' in mock_movimiento.motivo
    
    @patch('inventario.views.movimientos.logger')
    def test_confirmar_entrega_solo_salida(self, mock_logger):
        """Verifica que solo se pueden confirmar movimientos de salida."""
        from inventario.views.movimientos import MovimientoViewSet
        
        # Mock del movimiento de ENTRADA
        mock_movimiento = MagicMock()
        mock_movimiento.id = 2
        mock_movimiento.tipo = 'entrada'  # No es salida
        
        mock_user = MagicMock()
        mock_user.username = 'admin_test'
        
        request = self.factory.post('/api/movimientos/2/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 2}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            response = viewset.confirmar_entrega(request, pk=2)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'salida' in response.data['message'].lower()
    
    @patch('inventario.views.movimientos.logger')
    def test_confirmar_entrega_ya_confirmada(self, mock_logger):
        """Verifica que no se puede confirmar una entrega ya confirmada."""
        from inventario.views.movimientos import MovimientoViewSet
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 3
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = '[CONFIRMADO] Ya confirmado anteriormente'
        
        mock_user = MagicMock()
        mock_user.username = 'admin_test'
        
        request = self.factory.post('/api/movimientos/3/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 3}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            with patch('inventario.views.movimientos.is_farmacia_or_admin', return_value=True):
                response = viewset.confirmar_entrega(request, pk=3)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'ya fue confirmada' in response.data['message'].lower()
    
    @patch('inventario.views.movimientos.logger')
    def test_confirmar_entrega_preserva_motivo_original(self, mock_logger):
        """Verifica que el motivo original se preserva."""
        from inventario.views.movimientos import MovimientoViewSet
        
        motivo_original = 'Salida importante para farmacia'
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 4
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = motivo_original
        mock_movimiento.centro_destino = MagicMock()
        
        mock_user = MagicMock()
        mock_user.username = 'admin_test'
        
        request = self.factory.post('/api/movimientos/4/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 4}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            with patch('inventario.views.movimientos.is_farmacia_or_admin', return_value=True):
                response = viewset.confirmar_entrega(request, pk=4)
        
        assert response.status_code == status.HTTP_200_OK
        # Verificar que el motivo original está en el nuevo motivo
        assert motivo_original in mock_movimiento.motivo
        assert '[CONFIRMADO]' in mock_movimiento.motivo
    
    @patch('inventario.views.movimientos.logger')
    @patch('inventario.views.movimientos.is_farmacia_or_admin')
    @patch('inventario.views.movimientos.get_user_centro')
    def test_confirmar_entrega_usuario_otro_centro_prohibido(
        self, mock_get_centro, mock_is_admin, mock_logger
    ):
        """Usuario de otro centro NO puede confirmar entrega."""
        from inventario.views.movimientos import MovimientoViewSet
        
        mock_is_admin.return_value = False
        
        # Usuario pertenece al centro 1
        mock_centro_usuario = MagicMock()
        mock_centro_usuario.id = 1
        mock_get_centro.return_value = mock_centro_usuario
        
        # Movimiento va al centro 2
        mock_centro_destino = MagicMock()
        mock_centro_destino.id = 2  # Centro diferente
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 5
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = 'Salida para otro centro'
        mock_movimiento.centro_destino = mock_centro_destino
        
        mock_user = MagicMock()
        mock_user.username = 'user_centro1'
        
        request = self.factory.post('/api/movimientos/5/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 5}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            response = viewset.confirmar_entrega(request, pk=5)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'permiso' in response.data['message'].lower()
    
    @patch('inventario.views.movimientos.logger')
    @patch('inventario.views.movimientos.is_farmacia_or_admin')
    @patch('inventario.views.movimientos.get_user_centro')
    def test_confirmar_entrega_usuario_centro_destino_permitido(
        self, mock_get_centro, mock_is_admin, mock_logger
    ):
        """Usuario del centro destino SÍ puede confirmar su entrega."""
        from inventario.views.movimientos import MovimientoViewSet
        
        mock_is_admin.return_value = False
        
        # Usuario y movimiento del mismo centro
        mock_centro = MagicMock()
        mock_centro.id = 2
        mock_get_centro.return_value = mock_centro
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 6
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = 'Salida para mi centro'
        mock_movimiento.centro_destino = mock_centro  # Mismo centro
        
        mock_user = MagicMock()
        mock_user.username = 'user_centro2'
        
        request = self.factory.post('/api/movimientos/6/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 6}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            response = viewset.confirmar_entrega(request, pk=6)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] == True
    
    @patch('inventario.views.movimientos.logger')
    def test_confirmar_entrega_response_incluye_movimiento_id(self, mock_logger):
        """La respuesta incluye el ID del movimiento confirmado."""
        from inventario.views.movimientos import MovimientoViewSet
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 7
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = 'Test ID en respuesta'
        mock_movimiento.centro_destino = MagicMock()
        
        mock_user = MagicMock()
        mock_user.username = 'admin_test'
        
        request = self.factory.post('/api/movimientos/7/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 7}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            with patch('inventario.views.movimientos.is_farmacia_or_admin', return_value=True):
                response = viewset.confirmar_entrega(request, pk=7)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'movimiento_id' in response.data
        assert response.data['movimiento_id'] == 7
    
    @patch('inventario.views.movimientos.logger')
    def test_confirmar_entrega_movimiento_no_existe(self, mock_logger):
        """Error 404 cuando el movimiento no existe."""
        from inventario.views.movimientos import MovimientoViewSet
        from core.models import Movimiento
        
        mock_user = MagicMock()
        mock_user.username = 'admin_test'
        
        request = self.factory.post('/api/movimientos/99999/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 99999}
        
        with patch.object(viewset, 'get_object', side_effect=Movimiento.DoesNotExist):
            response = viewset.confirmar_entrega(request, pk=99999)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @patch('inventario.views.movimientos.logger')
    def test_confirmar_entrega_motivo_vacio(self, mock_logger):
        """Funciona correctamente si motivo está vacío."""
        from inventario.views.movimientos import MovimientoViewSet
        
        mock_movimiento = MagicMock()
        mock_movimiento.id = 8
        mock_movimiento.tipo = 'salida'
        mock_movimiento.motivo = None  # Motivo vacío
        mock_movimiento.centro_destino = MagicMock()
        
        mock_user = MagicMock()
        mock_user.username = 'admin_test'
        
        request = self.factory.post('/api/movimientos/8/confirmar-entrega/')
        request.user = mock_user
        
        viewset = MovimientoViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': 8}
        
        with patch.object(viewset, 'get_object', return_value=mock_movimiento):
            with patch('inventario.views.movimientos.is_farmacia_or_admin', return_value=True):
                response = viewset.confirmar_entrega(request, pk=8)
        
        assert response.status_code == status.HTTP_200_OK
        assert '[CONFIRMADO]' in mock_movimiento.motivo


class TestConfirmarEntregaURLExiste(TestCase):
    """Tests para verificar que el action está registrado correctamente."""
    
    def test_action_confirmar_entrega_definido(self):
        """Verifica que el método confirmar_entrega existe en el ViewSet."""
        from inventario.views.movimientos import MovimientoViewSet
        
        assert hasattr(MovimientoViewSet, 'confirmar_entrega')
        
        # Verificar que es un action
        method = getattr(MovimientoViewSet, 'confirmar_entrega')
        assert hasattr(method, 'detail')
        assert method.detail == True  # Es un action de detalle
        assert 'post' in method.mapping.keys()
    
    def test_action_url_path_correcto(self):
        """Verifica que el url_path es 'confirmar-entrega'."""
        from inventario.views.movimientos import MovimientoViewSet
        
        method = getattr(MovimientoViewSet, 'confirmar_entrega')
        assert method.url_path == 'confirmar-entrega'


# Para ejecutar: pytest backend/tests/test_confirmar_entrega.py -v
