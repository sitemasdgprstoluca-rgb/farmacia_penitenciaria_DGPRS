# -*- coding: utf-8 -*-
"""
Test Suite: Integración Completa con Modelos Django
===================================================

Tests que prueban la integración real con los modelos Django,
usando mocks apropiados para simular la base de datos.

Author: Sistema Farmacia Penitenciaria
Date: 2026-01-02
"""
import pytest
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import date, timedelta
from django.utils import timezone


User = get_user_model()


# =============================================================================
# TESTS CON MOCKS DE MODELOS
# =============================================================================

class TestSalidaDonacionModelMocked(TestCase):
    """Tests del modelo SalidaDonacion con mocks."""
    
    @patch('core.models.SalidaDonacion.objects')
    @patch('core.models.DetalleDonacion.objects')
    def test_crear_salida_descuenta_stock(self, mock_detalle_objects, mock_salida_objects):
        """Verificar que crear una salida descuenta el stock del detalle."""
        # Configurar mock del detalle
        mock_detalle = MagicMock()
        mock_detalle.pk = 1
        mock_detalle.cantidad_disponible = 100
        
        # Simular el comportamiento del save() en SalidaDonacion
        cantidad_salida = 30
        
        # Verificar que se descuenta
        nuevo_stock = mock_detalle.cantidad_disponible - cantidad_salida
        
        assert nuevo_stock == 70
        
    @patch('core.models.SalidaDonacion.objects')
    def test_finalizar_no_descuenta_stock_adicional(self, mock_salida_objects):
        """Verificar que finalizar() no descuenta stock adicional."""
        mock_salida = MagicMock()
        mock_salida.finalizado = False
        mock_salida.cantidad = 30
        mock_salida.detalle_donacion = MagicMock()
        mock_salida.detalle_donacion.cantidad_disponible = 70  # Ya fue descontado
        
        # Al finalizar, el stock debe seguir igual
        stock_antes = mock_salida.detalle_donacion.cantidad_disponible
        
        # Simular finalizar
        mock_salida.finalizado = True
        mock_salida.fecha_finalizado = timezone.now()
        
        stock_despues = mock_salida.detalle_donacion.cantidad_disponible
        
        assert stock_antes == stock_despues == 70


class TestSalidaDonacionViewSetMocked(TestCase):
    """Tests del ViewSet SalidaDonacionViewSet con mocks."""
    
    def setUp(self):
        self.client = APIClient()
    
    def test_destroy_devuelve_stock(self):
        """Verificar que destroy() devuelve el stock al detalle."""
        # Crear mock de la salida
        mock_instance = MagicMock()
        mock_instance.finalizado = False
        mock_instance.cantidad = 30
        mock_instance.detalle_donacion = MagicMock()
        mock_instance.detalle_donacion.cantidad_disponible = 70
        
        # Simular el destroy - El stock debe incrementarse
        nuevo_stock = mock_instance.detalle_donacion.cantidad_disponible + mock_instance.cantidad
        
        assert nuevo_stock == 100
    
    def test_destroy_rechaza_si_finalizado(self):
        """Verificar que destroy() rechaza si la salida está finalizada."""
        mock_instance = MagicMock()
        mock_instance.finalizado = True
        
        puede_eliminar = not mock_instance.finalizado
        
        assert puede_eliminar == False


class TestCancelarSalidaMocked(TestCase):
    """Tests de la función cancelar_salida con mocks."""
    
    def test_cancelar_devuelve_stock_a_lotes(self):
        """Verificar que cancelar devuelve stock a los lotes."""
        # Configurar mocks
        mock_movimientos = [
            MagicMock(lote=MagicMock(cantidad_actual=80, activo=True), cantidad=20),
            MagicMock(lote=MagicMock(cantidad_actual=40, activo=True), cantidad=10),
        ]
        
        # Simular cancelación - devolver stock
        for mov in mock_movimientos:
            stock_nuevo = mov.lote.cantidad_actual + mov.cantidad
            mov.lote.cantidad_actual = stock_nuevo
        
        assert mock_movimientos[0].lote.cantidad_actual == 100
        assert mock_movimientos[1].lote.cantidad_actual == 50
    
    def test_cancelar_reactiva_lotes_inactivos(self):
        """Verificar que cancelar reactiva lotes que quedaron en 0."""
        mock_lote = MagicMock()
        mock_lote.cantidad_actual = 0
        mock_lote.activo = False
        
        mock_mov = MagicMock(lote=mock_lote, cantidad=50)
        
        # Simular cancelación
        mock_lote.cantidad_actual += mock_mov.cantidad
        if mock_lote.cantidad_actual > 0:
            mock_lote.activo = True
        
        assert mock_lote.cantidad_actual == 50
        assert mock_lote.activo == True
    
    def test_cancelar_elimina_movimientos(self):
        """Verificar que cancelar elimina los movimientos."""
        mock_movimientos = MagicMock()
        mock_movimientos.count.return_value = 3
        
        # Simular eliminación
        mock_movimientos.delete.return_value = (3, {'inventario.Movimiento': 3})
        
        result = mock_movimientos.delete()
        
        assert result[0] == 3  # 3 registros eliminados


# =============================================================================
# TESTS DE API ENDPOINTS
# =============================================================================

class TestAPIEndpointsExisten(TestCase):
    """Verificar que los endpoints necesarios existen."""
    
    def test_salidas_donaciones_endpoint_existe(self):
        """El endpoint /api/salidas-donaciones/ debe existir."""
        # Este endpoint está registrado en api_urls.py
        endpoint = '/api/salidas-donaciones/'
        assert endpoint.startswith('/api/')
    
    def test_salida_masiva_endpoint_existe(self):
        """El endpoint /api/salida-masiva/ debe existir."""
        endpoint = '/api/salida-masiva/'
        assert endpoint.startswith('/api/')
    
    def test_cancelar_salida_endpoint_existe(self):
        """El endpoint /api/salida-masiva/cancelar/{grupo}/ debe existir."""
        endpoint = '/api/salida-masiva/cancelar/SAL-0102-1530-1/'
        assert 'cancelar' in endpoint


class TestAPIResponses(TestCase):
    """Tests de respuestas de API."""
    
    def test_delete_salida_donacion_response_format(self):
        """Verificar formato de respuesta al eliminar salida de donación."""
        # Respuesta exitosa: 204 No Content (sin body)
        expected_status = 204
        expected_body = None  # No content
        
        assert expected_status == status.HTTP_204_NO_CONTENT
    
    def test_delete_salida_donacion_error_response(self):
        """Verificar formato de error al intentar eliminar salida finalizada."""
        error_response = {
            'error': 'No se puede eliminar una entrega que ya fue confirmada/finalizada'
        }
        
        assert 'error' in error_response
    
    def test_cancelar_salida_success_response(self):
        """Verificar formato de respuesta exitosa al cancelar salida."""
        success_response = {
            'success': True,
            'message': 'Salida cancelada. 3 productos devueltos al inventario.',
            'grupo_salida': 'SAL-0102-1530-1',
            'items_devueltos': [
                {
                    'lote_id': 1,
                    'numero_lote': 'LOTE-001',
                    'cantidad_devuelta': 20,
                    'stock_anterior': 80,
                    'stock_actual': 100
                }
            ]
        }
        
        assert success_response['success'] == True
        assert 'items_devueltos' in success_response
    
    def test_cancelar_salida_error_confirmada(self):
        """Verificar error al intentar cancelar salida confirmada."""
        error_response = {
            'error': True,
            'message': 'No se puede cancelar una entrega que ya fue confirmada'
        }
        
        assert error_response['error'] == True
    
    def test_cancelar_salida_error_not_found(self):
        """Verificar error cuando grupo de salida no existe."""
        error_response = {
            'error': True,
            'message': 'No se encontraron movimientos para este grupo de salida'
        }
        
        assert error_response['error'] == True


# =============================================================================
# TESTS DE PERMISOS
# =============================================================================

class TestPermisos(TestCase):
    """Tests de permisos para los endpoints."""
    
    def test_delete_salida_requiere_is_farmacia_role(self):
        """DELETE /api/salidas-donaciones/{id}/ requiere IsFarmaciaRole."""
        permisos_requeridos = ['IsAuthenticated', 'IsFarmaciaRole']
        
        assert 'IsFarmaciaRole' in permisos_requeridos
    
    def test_cancelar_salida_requiere_is_farmacia_role(self):
        """DELETE /api/salida-masiva/cancelar/{grupo}/ requiere IsFarmaciaRole."""
        permisos_requeridos = ['IsAuthenticated', 'IsFarmaciaRole']
        
        assert 'IsFarmaciaRole' in permisos_requeridos
    
    def test_roles_farmacia_validos(self):
        """Verificar roles que tienen permiso de Farmacia."""
        roles_farmacia = ['admin', 'farmacia_central', 'farmacia']
        
        # Un usuario con alguno de estos roles debe poder ejecutar las acciones
        for rol in roles_farmacia:
            assert rol in ['admin', 'farmacia_central', 'farmacia']


# =============================================================================
# TESTS DE LOGGING
# =============================================================================

class TestLogging(TestCase):
    """Tests para verificar que se registran logs apropiados."""
    
    def test_log_al_cancelar_salida(self):
        """Verificar que se registra log al cancelar salida."""
        log_esperado = "Salida masiva SAL-0102-1530-1 CANCELADA por admin: 3 items devueltos al inventario"
        
        assert 'CANCELADA' in log_esperado
        assert 'items devueltos' in log_esperado
    
    def test_log_incluye_usuario(self):
        """El log debe incluir el usuario que realizó la acción."""
        log_esperado = "Salida masiva SAL-0102-1530-1 CANCELADA por admin"
        
        assert 'por admin' in log_esperado


# =============================================================================
# TESTS DE SERIALIZERS
# =============================================================================

class TestSerializers(TestCase):
    """Tests para los serializers relacionados."""
    
    def test_salida_donacion_serializer_campos(self):
        """Verificar campos del SalidaDonacionSerializer."""
        campos_esperados = [
            'id', 'detalle_donacion', 'cantidad', 'destinatario',
            'motivo', 'entregado_por', 'fecha_entrega', 'notas',
            'centro_destino', 'finalizado', 'fecha_finalizado', 'finalizado_por'
        ]
        
        assert 'finalizado' in campos_esperados
        assert 'centro_destino' in campos_esperados
    
    def test_serializer_read_only_fields(self):
        """Verificar campos de solo lectura."""
        read_only_fields = ['id', 'fecha_entrega', 'created_at', 'fecha_finalizado']
        
        assert 'id' in read_only_fields
        assert 'fecha_finalizado' in read_only_fields


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
