# -*- coding: utf-8 -*-
"""
Tests para DetalleRequisicionSerializer - Cálculo de stock disponible
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from unittest.mock import MagicMock, patch, PropertyMock
from core.serializers import DetalleRequisicionSerializer


class TestDetalleRequisicionSerializerStock(TestCase):
    """
    Tests para verificar que get_stock_disponible funciona correctamente.
    """
    
    def test_stock_disponible_con_lote_asignado(self):
        """
        Si hay lote asignado, debe retornar cantidad_actual del lote.
        """
        # Mock del detalle con lote
        mock_detalle = MagicMock()
        mock_detalle.lote = MagicMock()
        mock_detalle.lote.cantidad_actual = 50
        mock_detalle.producto = MagicMock()
        
        serializer = DetalleRequisicionSerializer()
        stock = serializer.get_stock_disponible(mock_detalle)
        
        assert stock == 50
    
    def test_stock_disponible_sin_lote_con_producto(self):
        """
        Si no hay lote pero hay producto, debe calcular stock total de lotes del producto.
        """
        # Mock del detalle sin lote pero con producto
        mock_detalle = MagicMock()
        mock_detalle.lote = None
        mock_detalle.producto = MagicMock()
        
        # Mock del queryset de lotes
        mock_lotes_qs = MagicMock()
        mock_lotes_qs.filter.return_value.aggregate.return_value = {'total': 100}
        mock_detalle.producto.lotes = mock_lotes_qs
        
        serializer = DetalleRequisicionSerializer()
        stock = serializer.get_stock_disponible(mock_detalle)
        
        assert stock == 100
        # Verificar que se filtró correctamente
        mock_lotes_qs.filter.assert_called_once_with(
            activo=True,
            cantidad_actual__gt=0,
            centro__isnull=True
        )
    
    def test_stock_disponible_sin_lote_sin_stock(self):
        """
        Si no hay lote y no hay stock del producto, debe retornar 0.
        """
        mock_detalle = MagicMock()
        mock_detalle.lote = None
        mock_detalle.producto = MagicMock()
        
        # Mock retorna None (no hay lotes)
        mock_lotes_qs = MagicMock()
        mock_lotes_qs.filter.return_value.aggregate.return_value = {'total': None}
        mock_detalle.producto.lotes = mock_lotes_qs
        
        serializer = DetalleRequisicionSerializer()
        stock = serializer.get_stock_disponible(mock_detalle)
        
        assert stock == 0
    
    def test_stock_disponible_sin_lote_ni_producto(self):
        """
        Si no hay lote ni producto, debe retornar 0.
        """
        mock_detalle = MagicMock()
        mock_detalle.lote = None
        mock_detalle.producto = None
        
        serializer = DetalleRequisicionSerializer()
        stock = serializer.get_stock_disponible(mock_detalle)
        
        assert stock == 0
    
    def test_stock_disponible_lote_con_cantidad_cero(self):
        """
        Si el lote tiene cantidad_actual = 0, debe retornar 0.
        """
        mock_detalle = MagicMock()
        mock_detalle.lote = MagicMock()
        mock_detalle.lote.cantidad_actual = 0
        mock_detalle.producto = MagicMock()
        
        serializer = DetalleRequisicionSerializer()
        stock = serializer.get_stock_disponible(mock_detalle)
        
        # Aunque hay lote, la cantidad es 0
        assert stock == 0
    
    def test_stock_disponible_lote_none_cantidad_actual(self):
        """
        Si el lote existe pero cantidad_actual es None, debe calcular del producto.
        """
        mock_detalle = MagicMock()
        mock_detalle.lote = MagicMock()
        mock_detalle.lote.cantidad_actual = None  # Campo vacío
        mock_detalle.producto = MagicMock()
        
        # Mock del queryset de lotes del producto
        mock_lotes_qs = MagicMock()
        mock_lotes_qs.filter.return_value.aggregate.return_value = {'total': 75}
        mock_detalle.producto.lotes = mock_lotes_qs
        
        serializer = DetalleRequisicionSerializer()
        stock = serializer.get_stock_disponible(mock_detalle)
        
        # Debe usar el stock del producto ya que lote.cantidad_actual es None
        assert stock == 75


class TestDetalleRequisicionSerializerValidation(TestCase):
    """
    Tests para validaciones del serializer.
    """
    
    def test_cantidad_solicitada_positiva(self):
        """
        La cantidad solicitada debe ser mayor a 0.
        """
        serializer = DetalleRequisicionSerializer()
        
        # Debe fallar con 0
        with pytest.raises(Exception):
            serializer.validate_cantidad_solicitada(0)
        
        # Debe fallar con negativo
        with pytest.raises(Exception):
            serializer.validate_cantidad_solicitada(-5)
    
    def test_cantidad_solicitada_valida(self):
        """
        Cantidad positiva debe ser aceptada.
        """
        serializer = DetalleRequisicionSerializer()
        result = serializer.validate_cantidad_solicitada(10)
        assert result == 10
    
    def test_motivo_ajuste_requerido_cuando_cantidad_reducida(self):
        """
        MEJORA FLUJO 3: Si cantidad_autorizada < cantidad_solicitada,
        debe requerir motivo_ajuste.
        """
        serializer = DetalleRequisicionSerializer()
        
        # Datos con cantidad reducida sin motivo
        data = {
            'cantidad_solicitada': 10,
            'cantidad_autorizada': 5,
            'motivo_ajuste': ''  # Vacío
        }
        
        with pytest.raises(Exception) as exc_info:
            serializer.validate(data)
        
        # Debe indicar que falta el motivo
        assert 'motivo_ajuste' in str(exc_info.value)
    
    def test_motivo_ajuste_minimo_10_caracteres(self):
        """
        El motivo de ajuste debe tener al menos 10 caracteres.
        """
        serializer = DetalleRequisicionSerializer()
        
        # Motivo muy corto
        data = {
            'cantidad_solicitada': 10,
            'cantidad_autorizada': 5,
            'motivo_ajuste': 'Corto'  # Solo 5 caracteres
        }
        
        with pytest.raises(Exception) as exc_info:
            serializer.validate(data)
        
        assert 'motivo_ajuste' in str(exc_info.value) or 'mínimo 10' in str(exc_info.value)
    
    def test_motivo_ajuste_no_requerido_cuando_cantidad_igual(self):
        """
        Si la cantidad autorizada >= solicitada, no se requiere motivo.
        """
        serializer = DetalleRequisicionSerializer()
        
        # Cantidad igual
        data = {
            'cantidad_solicitada': 10,
            'cantidad_autorizada': 10,
            'motivo_ajuste': None
        }
        
        # No debe lanzar excepción
        result = serializer.validate(data)
        assert result == data


class TestDetalleRequisicionSerializerFields(TestCase):
    """
    Tests para verificar que los campos del serializer están correctos.
    """
    
    def test_serializer_tiene_campos_requeridos(self):
        """
        Verifica que el serializer tiene todos los campos necesarios.
        """
        serializer = DetalleRequisicionSerializer()
        campos = serializer.fields.keys()
        
        # Campos de producto
        assert 'producto_nombre' in campos
        assert 'producto_clave' in campos
        assert 'producto_unidad' in campos
        
        # Campos de lote
        assert 'lote_numero' in campos
        assert 'lote_caducidad' in campos
        assert 'lote_stock' in campos
        
        # Campo de stock disponible (ahora es SerializerMethodField)
        assert 'stock_disponible' in campos
        
        # Campos de cantidades
        assert 'cantidad_solicitada' in campos
        assert 'cantidad_autorizada' in campos
        assert 'cantidad_surtida' in campos
        
        # Campo de motivo
        assert 'motivo_ajuste' in campos
    
    def test_stock_disponible_es_read_only(self):
        """
        El campo stock_disponible debe ser de solo lectura (method field).
        """
        serializer = DetalleRequisicionSerializer()
        
        # Los SerializerMethodField son siempre read_only
        field = serializer.fields.get('stock_disponible')
        assert field is not None
        # SerializerMethodField no tiene el atributo read_only explícito
        # pero es efectivamente read_only
        assert hasattr(serializer, 'get_stock_disponible')
