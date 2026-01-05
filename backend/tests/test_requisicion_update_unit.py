"""
Pruebas unitarias exhaustivas para el proceso de actualización de requisiciones.

NOTA: Estas pruebas usan mocks para evitar problemas con managed=False.
No requieren base de datos real, solo validan la lógica del endpoint.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from rest_framework import status
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model


class TestRequisicionUpdateLogica:
    """
    Tests unitarios para la lógica de actualización de requisiciones.
    Usa mocks para evitar dependencia de base de datos.
    """
    
    @pytest.fixture
    def factory(self):
        return APIRequestFactory()
    
    @pytest.fixture
    def mock_user_farmacia(self):
        """Usuario farmacia con todos los permisos."""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.is_staff = True
        user.rol = 'farmacia'
        user.id = 1
        user.centro = None
        user.centro_id = None
        return user
    
    @pytest.fixture
    def mock_user_medico(self):
        """Usuario médico de centro."""
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = False
        user.is_staff = False
        user.rol = 'medico'
        user.id = 2
        user.centro = Mock(id=100, nombre='Centro Test')
        user.centro_id = 100
        return user
    
    @pytest.fixture
    def mock_requisicion_borrador(self):
        """Requisición en estado borrador."""
        req = Mock()
        req.id = 1
        req.estado = 'borrador'
        req.centro_id = 100
        req.centro = Mock(id=100, nombre='Centro Test')
        req.detalles = Mock()
        req.detalles.all.return_value.delete = Mock()
        return req
    
    @pytest.fixture
    def mock_requisicion_enviada(self):
        """Requisición en estado enviada (no editable)."""
        req = Mock()
        req.id = 2
        req.estado = 'enviada'
        req.centro_id = 100
        req.centro = Mock(id=100, nombre='Centro Test')
        req.detalles = Mock()
        return req
    
    @pytest.fixture
    def mock_requisicion_devuelta(self):
        """Requisición devuelta (editable)."""
        req = Mock()
        req.id = 3
        req.estado = 'devuelta'
        req.centro_id = 100
        req.centro = Mock(id=100, nombre='Centro Test')
        req.detalles = Mock()
        req.detalles.all.return_value.delete = Mock()
        return req

    # =========================================================================
    # TESTS DE VALIDACIÓN DE ESTADO
    # =========================================================================
    
    def test_update_rechaza_estado_enviada(self, mock_requisicion_enviada, mock_user_medico):
        """No se puede editar una requisición ya enviada."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_enviada)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        viewset.request = Mock(user=mock_user_medico, data={'notas': 'test'})
        
        with patch.object(viewset, 'get_serializer'):
            response = viewset.update(viewset.request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'borrador' in response.data.get('error', '').lower() or 'devuelta' in response.data.get('error', '').lower()
    
    def test_update_permite_estado_borrador(self, mock_requisicion_borrador, mock_user_medico):
        """Se puede editar una requisición en borrador."""
        from inventario.views_legacy import RequisicionViewSet
        from core.serializers import RequisicionSerializer
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        viewset._validar_stock_items = Mock(return_value=[])
        
        # Mock del serializer
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=mock_requisicion_borrador)
        mock_serializer.data = {'id': 1, 'estado': 'borrador'}
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {'notas': 'actualizadas'}
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1, 'estado': 'borrador'}
            response = viewset.update(request)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_update_permite_estado_devuelta(self, mock_requisicion_devuelta, mock_user_medico):
        """Se puede editar una requisición devuelta para correcciones."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_devuelta)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        viewset._validar_stock_items = Mock(return_value=[])
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=mock_requisicion_devuelta)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {'notas': 'corregida'}
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 3, 'estado': 'devuelta'}
            response = viewset.update(request)
        
        assert response.status_code == status.HTTP_200_OK

    # =========================================================================
    # TESTS DE CONTROL DE ACCESO POR CENTRO
    # =========================================================================
    
    def test_update_rechaza_otro_centro(self, mock_requisicion_borrador, mock_user_medico):
        """Un usuario no puede editar requisiciones de otro centro."""
        from inventario.views_legacy import RequisicionViewSet
        
        # Requisición de centro diferente
        mock_requisicion_borrador.centro_id = 999  # Otro centro
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)  # Centro 100
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {}
        
        response = viewset.update(request)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'otro centro' in response.data.get('error', '').lower()
    
    def test_update_superuser_puede_editar_cualquier_centro(self, mock_requisicion_borrador):
        """Un superusuario puede editar requisiciones de cualquier centro."""
        from inventario.views_legacy import RequisicionViewSet
        
        superuser = Mock()
        superuser.is_authenticated = True
        superuser.is_superuser = True
        superuser.rol = 'admin_sistema'
        superuser.centro = None
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=None)
        viewset._validar_stock_items = Mock(return_value=[])
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=mock_requisicion_borrador)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = superuser
        request.data = {}
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            response = viewset.update(request)
        
        assert response.status_code == status.HTTP_200_OK

    # =========================================================================
    # TESTS DE DETALLES/ITEMS
    # =========================================================================
    
    def test_update_con_items_elimina_anteriores(self, mock_requisicion_borrador, mock_user_medico):
        """Al actualizar con items, se eliminan los detalles anteriores."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        viewset._validar_stock_items = Mock(return_value=[])
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=mock_requisicion_borrador)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {
            'notas': 'test',
            'items': [
                {'producto': 1, 'cantidad_solicitada': 10},
                {'producto': 2, 'cantidad_solicitada': 5}
            ]
        }
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            with patch('inventario.views_legacy.DetalleRequisicion') as MockDetalle:
                MockDetalle.objects.create = Mock()
                response = viewset.update(request)
        
        # Verificar que se llamó delete en los detalles anteriores
        mock_requisicion_borrador.detalles.all.return_value.delete.assert_called_once()
        assert response.status_code == status.HTTP_200_OK
    
    def test_update_ignora_items_sin_producto(self, mock_requisicion_borrador, mock_user_medico):
        """Los items sin producto_id son ignorados."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        viewset._validar_stock_items = Mock(return_value=[])
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=mock_requisicion_borrador)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {
            'items': [
                {'producto': None, 'cantidad_solicitada': 10},  # Sin producto
                {'cantidad_solicitada': 5},  # Sin campo producto
                {'producto': 1, 'cantidad_solicitada': None},  # Sin cantidad
            ]
        }
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            with patch('inventario.views_legacy.DetalleRequisicion') as MockDetalle:
                MockDetalle.objects.create = Mock()
                response = viewset.update(request)
        
        # No debe crear ningún detalle
        MockDetalle.objects.create.assert_not_called()

    # =========================================================================
    # TESTS DE VALIDACIÓN DE STOCK (modo informativo)
    # =========================================================================
    
    def test_update_incluye_advertencias_stock(self, mock_requisicion_borrador, mock_user_medico):
        """Las advertencias de stock se incluyen en la respuesta."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        
        # Simular advertencias de stock
        advertencias = [
            {'producto_id': 1, 'mensaje': 'Stock insuficiente: disponible 5, solicitado 10'}
        ]
        viewset._validar_stock_items = Mock(return_value=advertencias)
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=mock_requisicion_borrador)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {
            'items': [{'producto': 1, 'cantidad_solicitada': 10}]
        }
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            with patch('inventario.views_legacy.DetalleRequisicion') as MockDetalle:
                MockDetalle.objects.create = Mock()
                response = viewset.update(request)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'advertencias_stock' in response.data
        assert len(response.data['advertencias_stock']) == 1

    # =========================================================================
    # TESTS DE MANEJO DE ERRORES
    # =========================================================================
    
    def test_update_maneja_validation_error(self, mock_requisicion_borrador, mock_user_medico):
        """ValidationError se maneja correctamente y devuelve 400."""
        from inventario.views_legacy import RequisicionViewSet
        from django.core.exceptions import ValidationError
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        
        # Simular ValidationError en el serializer
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(side_effect=ValidationError({'cantidad': ['Debe ser positivo']}))
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {'items': [{'producto': 1, 'cantidad_solicitada': -5}]}
        
        response = viewset.update(request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_update_maneja_exception_generica(self, mock_requisicion_borrador, mock_user_medico):
        """Excepciones genéricas se manejan y devuelven 500 con mensaje."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        
        # Simular excepción genérica
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(side_effect=Exception('Error de base de datos'))
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {}
        
        response = viewset.update(request)
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert 'error' in response.data
        assert 'Error interno' in response.data['error']

    # =========================================================================
    # TESTS DE CAMPOS ESPECÍFICOS
    # =========================================================================
    
    def test_update_acepta_detalles_o_items(self, mock_requisicion_borrador, mock_user_medico):
        """El endpoint acepta tanto 'items' como 'detalles' en el request."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        viewset._validar_stock_items = Mock(return_value=[])
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=mock_requisicion_borrador)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        # Usando 'detalles' en lugar de 'items'
        request = Mock()
        request.user = mock_user_medico
        request.data = {
            'detalles': [{'producto': 1, 'cantidad_solicitada': 10}]
        }
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            with patch('inventario.views_legacy.DetalleRequisicion') as MockDetalle:
                MockDetalle.objects.create = Mock()
                response = viewset.update(request)
        
        assert response.status_code == status.HTTP_200_OK
        MockDetalle.objects.create.assert_called_once()
    
    def test_update_guarda_lote_especifico(self, mock_requisicion_borrador, mock_user_medico):
        """Se puede especificar un lote específico en los items."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        viewset._validar_stock_items = Mock(return_value=[])
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=mock_requisicion_borrador)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {
            'items': [{'producto': 1, 'cantidad_solicitada': 10, 'lote_id': 5}]
        }
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            with patch('inventario.views_legacy.DetalleRequisicion') as MockDetalle:
                MockDetalle.objects.create = Mock()
                response = viewset.update(request)
        
        # Verificar que se pasó el lote_id
        call_args = MockDetalle.objects.create.call_args
        assert call_args.kwargs.get('lote_id') == 5
    
    def test_update_usa_notas_no_observaciones(self, mock_requisicion_borrador, mock_user_medico):
        """Se usa 'notas' en lugar de 'observaciones' (que es @property)."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=mock_requisicion_borrador)
        viewset._user_centro = Mock(return_value=mock_user_medico.centro)
        viewset._validar_stock_items = Mock(return_value=[])
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=mock_requisicion_borrador)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        request = Mock()
        request.user = mock_user_medico
        request.data = {
            'items': [
                {'producto': 1, 'cantidad_solicitada': 10, 'observaciones': 'Nota del item'}
            ]
        }
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            with patch('inventario.views_legacy.DetalleRequisicion') as MockDetalle:
                MockDetalle.objects.create = Mock()
                response = viewset.update(request)
        
        # Verificar que se usó 'notas' con el valor de 'observaciones'
        call_args = MockDetalle.objects.create.call_args
        assert call_args.kwargs.get('notas') == 'Nota del item'


class TestRequisicionUpdateEstadosInvalidos:
    """Tests para verificar que estados no editables son rechazados."""
    
    @pytest.fixture
    def viewset_setup(self):
        """Setup común para tests de estados."""
        from inventario.views_legacy import RequisicionViewSet
        
        viewset = RequisicionViewSet()
        user = Mock()
        user.is_authenticated = True
        user.is_superuser = True
        user.rol = 'admin_sistema'
        
        return viewset, user
    
    @pytest.mark.parametrize("estado_invalido", [
        'enviada',
        'autorizada',
        'autorizada_admin',
        'autorizada_director',
        'recibida_farmacia',
        'autorizada_farmacia',
        'surtida',
        'en_transito',
        'entregada',
        'recibida',
        'rechazada',  # Solo se puede reenviar, no editar
        'cancelada',
        'vencida',
    ])
    def test_update_rechaza_estados_no_editables(self, viewset_setup, estado_invalido):
        """Verifica que todos los estados no editables son rechazados."""
        viewset, user = viewset_setup
        
        requisicion = Mock()
        requisicion.id = 1
        requisicion.estado = estado_invalido
        requisicion.centro_id = 100
        
        viewset.get_object = Mock(return_value=requisicion)
        viewset._user_centro = Mock(return_value=None)
        
        request = Mock()
        request.user = user
        request.data = {}
        
        response = viewset.update(request)
        
        # Solo borrador y devuelta son editables
        if estado_invalido not in ['borrador', 'devuelta']:
            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestRequisicionUpdateIntegracion:
    """
    Tests de integración simulados para el flujo completo.
    Verifica escenarios reales del flujo de requisiciones.
    """
    
    def test_flujo_medico_crea_y_edita(self):
        """
        Escenario: Médico crea requisición, la edita, luego la envía.
        """
        from inventario.views_legacy import RequisicionViewSet
        
        # Setup
        medico = Mock()
        medico.is_authenticated = True
        medico.is_superuser = False
        medico.rol = 'medico'
        medico.centro = Mock(id=100)
        medico.centro_id = 100
        
        requisicion = Mock()
        requisicion.id = 1
        requisicion.estado = 'borrador'
        requisicion.centro_id = 100
        requisicion.centro = medico.centro
        requisicion.detalles = Mock()
        requisicion.detalles.all.return_value.delete = Mock()
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=requisicion)
        viewset._user_centro = Mock(return_value=medico.centro)
        viewset._validar_stock_items = Mock(return_value=[])
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=requisicion)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        # Primera edición
        request1 = Mock()
        request1.user = medico
        request1.data = {'notas': 'Primera versión', 'items': []}
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            response1 = viewset.update(request1)
        
        assert response1.status_code == status.HTTP_200_OK
        
        # Segunda edición (agregar items)
        request2 = Mock()
        request2.user = medico
        request2.data = {
            'notas': 'Con medicamentos',
            'items': [
                {'producto': 1, 'cantidad_solicitada': 20}
            ]
        }
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            with patch('inventario.views_legacy.DetalleRequisicion') as MockDetalle:
                MockDetalle.objects.create = Mock()
                response2 = viewset.update(request2)
        
        assert response2.status_code == status.HTTP_200_OK
    
    def test_flujo_devolucion_y_correccion(self):
        """
        Escenario: Requisición devuelta por admin, médico la corrige.
        """
        from inventario.views_legacy import RequisicionViewSet
        
        medico = Mock()
        medico.is_authenticated = True
        medico.is_superuser = False
        medico.rol = 'medico'
        medico.centro = Mock(id=100)
        medico.centro_id = 100
        
        # Requisición devuelta
        requisicion = Mock()
        requisicion.id = 1
        requisicion.estado = 'devuelta'
        requisicion.centro_id = 100
        requisicion.centro = medico.centro
        requisicion.detalles = Mock()
        requisicion.detalles.all.return_value.delete = Mock()
        
        viewset = RequisicionViewSet()
        viewset.get_object = Mock(return_value=requisicion)
        viewset._user_centro = Mock(return_value=medico.centro)
        viewset._validar_stock_items = Mock(return_value=[])
        
        mock_serializer = Mock()
        mock_serializer.is_valid = Mock(return_value=True)
        mock_serializer.save = Mock(return_value=requisicion)
        viewset.get_serializer = Mock(return_value=mock_serializer)
        
        # Médico corrige la requisición devuelta
        request = Mock()
        request.user = medico
        request.data = {
            'notas': 'Corregida según indicaciones',
            'items': [
                {'producto': 1, 'cantidad_solicitada': 10}  # Cantidad corregida
            ]
        }
        
        with patch('inventario.views_legacy.RequisicionSerializer') as MockSerializer:
            MockSerializer.return_value.data = {'id': 1}
            with patch('inventario.views_legacy.DetalleRequisicion') as MockDetalle:
                MockDetalle.objects.create = Mock()
                response = viewset.update(request)
        
        assert response.status_code == status.HTTP_200_OK
        # Verificar que se eliminaron items anteriores
        requisicion.detalles.all.return_value.delete.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
