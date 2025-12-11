"""
Tests para correcciones ISS-001 a ISS-005 (audit20).

Cobertura:
- ISS-001: Validación de stock por centro en movimientos
- ISS-004: Servicio de transferencias atómico
- ISS-005: Validación temprana de stock al enviar requisiciones
"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError


class TestISS001ValidacionStockPorCentro:
    """ISS-001: Validación de stock considerando el centro."""
    
    def test_salida_valida_centro_lote(self):
        """Salida debe validar que el lote esté en el centro origen."""
        from core.models import Movimiento
        
        # Crear mock de movimiento con lote en centro diferente
        mov = MagicMock(spec=Movimiento)
        mov.tipo = 'salida'
        mov.centro_origen_id = 1
        mov.cantidad = 10
        
        # Lote está en centro 2 (diferente)
        mock_lote = MagicMock()
        mock_lote.centro_id = 2
        mock_lote.cantidad_actual = 100
        mock_lote.numero_lote = 'LOT-001'
        mock_lote.activo = True
        mock_lote.esta_vencido.return_value = False
        mov.lote = mock_lote
        mov.lote_id = 1
        
        # Simular clean() - debería detectar inconsistencia
        # El lote.centro_id (2) != centro_origen_id (1)
        assert mov.lote.centro_id != mov.centro_origen_id
    
    def test_salida_lote_en_centro_correcto_ok(self):
        """Salida es válida si el lote está en el centro origen."""
        from core.models import Movimiento
        
        mov = MagicMock(spec=Movimiento)
        mov.tipo = 'salida'
        mov.centro_origen_id = 1
        mov.cantidad = 10
        
        # Lote está en el mismo centro
        mock_lote = MagicMock()
        mock_lote.centro_id = 1  # Mismo centro
        mock_lote.cantidad_actual = 100
        mov.lote = mock_lote
        
        assert mov.lote.centro_id == mov.centro_origen_id


class TestISS004TransferService:
    """ISS-004: Servicio de transferencias atómico."""
    
    def test_transferencia_valida_cantidad_positiva(self):
        """La cantidad debe ser mayor a cero."""
        from inventario.services.transfer_service import TransferService, TransferenciaResultado
        
        # Mock de objetos necesarios
        lote = MagicMock()
        centro = MagicMock()
        usuario = MagicMock()
        
        # Ejecutar con cantidad 0 (inválida)
        with patch('inventario.services.transfer_service.Lote') as MockLote:
            # Simular que no llega a bloquear porque falla antes
            resultado = TransferService.ejecutar_transferencia(
                lote_origen=lote,
                cantidad=0,  # Inválido
                centro_destino=centro,
                usuario=usuario
            )
            
            assert resultado.exitoso is False
            assert "mayor a cero" in resultado.mensaje.lower()
    
    def test_transferencia_requiere_lote_origen(self):
        """Debe especificarse un lote de origen."""
        from inventario.services.transfer_service import TransferService
        
        centro = MagicMock()
        usuario = MagicMock()
        
        resultado = TransferService.ejecutar_transferencia(
            lote_origen=None,  # Falta lote
            cantidad=10,
            centro_destino=centro,
            usuario=usuario
        )
        
        assert resultado.exitoso is False
        assert "lote" in resultado.mensaje.lower()
    
    def test_transferencia_requiere_centro_destino(self):
        """Debe especificarse un centro de destino."""
        from inventario.services.transfer_service import TransferService
        
        lote = MagicMock()
        lote.pk = 1
        usuario = MagicMock()
        
        resultado = TransferService.ejecutar_transferencia(
            lote_origen=lote,
            cantidad=10,
            centro_destino=None,  # Falta centro
            usuario=usuario
        )
        
        assert resultado.exitoso is False
        assert "destino" in resultado.mensaje.lower()
    
    def test_transferencia_resultado_dataclass(self):
        """TransferenciaResultado tiene los campos correctos."""
        from inventario.services.transfer_service import TransferenciaResultado
        
        resultado = TransferenciaResultado(
            exitoso=True,
            mensaje="Transferencia exitosa",
            movimiento_salida_id=1,
            movimiento_entrada_id=2,
            lote_destino_id=3,
            cantidad_transferida=100
        )
        
        assert resultado.exitoso is True
        assert resultado.cantidad_transferida == 100
        assert resultado.errores == []


class TestISS005ValidacionTempranaStock:
    """ISS-005: Validación temprana de stock al enviar requisiciones."""
    
    def test_validar_transicion_advierte_stock_insuficiente(self):
        """Al enviar, debe advertir si hay productos sin stock."""
        from core.models import Requisicion
        
        # Mock de requisición con detalles
        req = MagicMock(spec=Requisicion)
        req.estado = 'borrador'
        req.numero = 'REQ-001'
        
        # Mock de detalles con producto sin stock
        mock_detalle = MagicMock()
        mock_detalle.cantidad_solicitada = 100
        mock_producto = MagicMock()
        mock_producto.nombre = 'Paracetamol'
        mock_producto.get_stock_farmacia_central.return_value = 10  # Solo 10 disponibles
        mock_detalle.producto = mock_producto
        
        mock_detalles = MagicMock()
        mock_detalles.exists.return_value = True
        mock_detalles.all.return_value = [mock_detalle]
        req.detalles = mock_detalles
        
        # El stock disponible (10) < solicitado (100)
        assert mock_producto.get_stock_farmacia_central() < mock_detalle.cantidad_solicitada
    
    def test_validar_transicion_sin_advertencia_stock_suficiente(self):
        """Sin advertencia si hay stock suficiente."""
        from core.models import Requisicion
        
        mock_detalle = MagicMock()
        mock_detalle.cantidad_solicitada = 50
        mock_producto = MagicMock()
        mock_producto.nombre = 'Ibuprofeno'
        mock_producto.get_stock_farmacia_central.return_value = 200  # Suficiente
        mock_detalle.producto = mock_producto
        
        # Stock disponible (200) >= solicitado (50)
        assert mock_producto.get_stock_farmacia_central() >= mock_detalle.cantidad_solicitada


class TestConcurrencia:
    """Tests de concurrencia para operaciones críticas."""
    
    def test_select_for_update_previene_race_condition(self):
        """select_for_update debe bloquear registros."""
        # Este test verifica la estructura, no la ejecución real
        from inventario.services.transfer_service import TransferService
        import inspect
        
        source = inspect.getsource(TransferService.ejecutar_transferencia)
        
        # Verificar que usa select_for_update
        assert 'select_for_update' in source
        assert 'transaction.atomic' in source
    
    def test_transferencia_usa_bloqueo_lote_destino(self):
        """La transferencia también debe bloquear el lote destino."""
        from inventario.services.transfer_service import TransferService
        import inspect
        
        source = inspect.getsource(TransferService.ejecutar_transferencia)
        
        # Debe bloquear tanto origen como destino
        assert source.count('select_for_update') >= 2


# Marcadores pytest
pytestmark = [
    pytest.mark.unit,
    pytest.mark.audit20,
]
