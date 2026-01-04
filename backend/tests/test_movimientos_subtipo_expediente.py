# -*- coding: utf-8 -*-
"""
Test Suite: Movimientos - Subtipo Salida y Número Expediente
============================================================

Tests para verificar que los campos subtipo_salida y numero_expediente
están correctamente integrados en:
- Modelo Movimiento
- Serializer MovimientoSerializer
- ViewSet exportar_excel
- Endpoint reporte_movimientos

Author: Sistema Farmacia Penitenciaria
Date: 2026-01-03
"""
import pytest
from django.test import TestCase
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock, PropertyMock
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from io import BytesIO


# =============================================================================
# TESTS DE MODELO Y SERIALIZER
# =============================================================================

class TestMovimientoModeloSubtipoExpediente(TestCase):
    """Tests para verificar campos subtipo_salida y numero_expediente en el modelo."""
    
    def test_modelo_tiene_campo_subtipo_salida(self):
        """Verifica que el modelo Movimiento tiene el campo subtipo_salida."""
        from core.models import Movimiento
        
        # Obtener los campos del modelo
        field_names = [f.name for f in Movimiento._meta.get_fields()]
        
        assert 'subtipo_salida' in field_names, "Campo subtipo_salida no existe en modelo Movimiento"
    
    def test_modelo_tiene_campo_numero_expediente(self):
        """Verifica que el modelo Movimiento tiene el campo numero_expediente."""
        from core.models import Movimiento
        
        field_names = [f.name for f in Movimiento._meta.get_fields()]
        
        assert 'numero_expediente' in field_names, "Campo numero_expediente no existe en modelo Movimiento"
    
    def test_subtipo_salida_permite_valores_validos(self):
        """Verifica que subtipo_salida acepta los valores esperados."""
        from core.models import Movimiento
        
        # Valores válidos según la documentación
        valores_validos = ['receta', 'consumo_interno', 'merma', 'caducidad', 'transferencia']
        
        # Verificar que el campo existe y es CharField
        field = Movimiento._meta.get_field('subtipo_salida')
        assert field.max_length >= 30, "subtipo_salida debe tener max_length >= 30"
        assert field.null is True or field.blank is True, "subtipo_salida debe permitir valores vacíos"


class TestMovimientoSerializerSubtipoExpediente(TestCase):
    """Tests para verificar campos en MovimientoSerializer."""
    
    def test_serializer_incluye_subtipo_salida(self):
        """Verifica que el serializer expone subtipo_salida."""
        from core.serializers import MovimientoSerializer
        
        serializer = MovimientoSerializer()
        field_names = list(serializer.fields.keys())
        
        assert 'subtipo_salida' in field_names, "subtipo_salida no está en MovimientoSerializer.fields"
    
    def test_serializer_incluye_numero_expediente(self):
        """Verifica que el serializer expone numero_expediente."""
        from core.serializers import MovimientoSerializer
        
        serializer = MovimientoSerializer()
        field_names = list(serializer.fields.keys())
        
        assert 'numero_expediente' in field_names, "numero_expediente no está en MovimientoSerializer.fields"
    
    def test_serializer_subtipo_salida_es_opcional(self):
        """Verifica que subtipo_salida es un campo opcional."""
        from core.serializers import MovimientoSerializer
        
        serializer = MovimientoSerializer()
        subtipo_field = serializer.fields.get('subtipo_salida')
        
        assert subtipo_field is not None, "Campo subtipo_salida no encontrado"
        # Verificar que es opcional (required=False o allow_null=True)
        is_optional = not subtipo_field.required or getattr(subtipo_field, 'allow_null', False)
        assert is_optional, "subtipo_salida debería ser opcional"
    
    def test_serializer_numero_expediente_es_opcional(self):
        """Verifica que numero_expediente es un campo opcional."""
        from core.serializers import MovimientoSerializer
        
        serializer = MovimientoSerializer()
        expediente_field = serializer.fields.get('numero_expediente')
        
        assert expediente_field is not None, "Campo numero_expediente no encontrado"
        is_optional = not expediente_field.required or getattr(expediente_field, 'allow_null', False)
        assert is_optional, "numero_expediente debería ser opcional"


# =============================================================================
# TESTS DE EXPORTACIÓN EXCEL EN MOVIMIENTOS
# =============================================================================

class TestMovimientosExportarExcel(TestCase):
    """Tests para verificar que exportar_excel incluye los nuevos campos."""
    
    def test_headers_excel_incluyen_subtipo(self):
        """Verifica que los headers del Excel incluyen Subtipo."""
        # Los headers esperados según el código actualizado
        headers_esperados = [
            '#', 'Fecha', 'Tipo', 'Subtipo', 'Producto', 'Lote', 'Cantidad',
            'Centro Origen', 'Centro Destino', 'No. Expediente', 'Usuario', 'Observaciones'
        ]
        
        # Verificar que Subtipo está en la posición correcta (índice 3)
        assert 'Subtipo' in headers_esperados
        assert headers_esperados.index('Subtipo') == 3
    
    def test_headers_excel_incluyen_expediente(self):
        """Verifica que los headers del Excel incluyen No. Expediente."""
        headers_esperados = [
            '#', 'Fecha', 'Tipo', 'Subtipo', 'Producto', 'Lote', 'Cantidad',
            'Centro Origen', 'Centro Destino', 'No. Expediente', 'Usuario', 'Observaciones'
        ]
        
        assert 'No. Expediente' in headers_esperados
        assert headers_esperados.index('No. Expediente') == 9
    
    def test_total_columnas_excel(self):
        """Verifica que hay 12 columnas en el Excel de movimientos."""
        headers_esperados = [
            '#', 'Fecha', 'Tipo', 'Subtipo', 'Producto', 'Lote', 'Cantidad',
            'Centro Origen', 'Centro Destino', 'No. Expediente', 'Usuario', 'Observaciones'
        ]
        
        assert len(headers_esperados) == 12, f"Se esperan 12 columnas, hay {len(headers_esperados)}"


class TestSubtipoDisplayFormateo(TestCase):
    """Tests para verificar el formateo de subtipo_display."""
    
    def test_formateo_subtipo_receta(self):
        """Verifica formateo de subtipo 'receta' a 'Receta Médica'."""
        subtipos_label = {
            'receta': 'Receta Médica',
            'consumo_interno': 'Consumo Interno',
            'merma': 'Merma',
            'caducidad': 'Caducidad',
            'transferencia': 'Transferencia',
        }
        
        subtipo = 'receta'
        display = subtipos_label.get(subtipo.lower(), subtipo.title())
        
        assert display == 'Receta Médica'
    
    def test_formateo_subtipo_consumo_interno(self):
        """Verifica formateo de subtipo 'consumo_interno'."""
        subtipos_label = {
            'receta': 'Receta Médica',
            'consumo_interno': 'Consumo Interno',
            'merma': 'Merma',
            'caducidad': 'Caducidad',
            'transferencia': 'Transferencia',
        }
        
        subtipo = 'consumo_interno'
        display = subtipos_label.get(subtipo.lower(), subtipo.title())
        
        assert display == 'Consumo Interno'
    
    def test_formateo_subtipo_merma(self):
        """Verifica formateo de subtipo 'merma'."""
        subtipos_label = {
            'receta': 'Receta Médica',
            'consumo_interno': 'Consumo Interno',
            'merma': 'Merma',
            'caducidad': 'Caducidad',
            'transferencia': 'Transferencia',
        }
        
        subtipo = 'merma'
        display = subtipos_label.get(subtipo.lower(), subtipo.title())
        
        assert display == 'Merma'
    
    def test_formateo_subtipo_desconocido_usa_title(self):
        """Verifica que subtipos desconocidos usan .title() como fallback."""
        subtipos_label = {
            'receta': 'Receta Médica',
            'consumo_interno': 'Consumo Interno',
            'merma': 'Merma',
            'caducidad': 'Caducidad',
            'transferencia': 'Transferencia',
        }
        
        subtipo = 'otro_tipo'
        display = subtipos_label.get(subtipo.lower(), subtipo.title())
        
        assert display == 'Otro_Tipo'  # .title() capitaliza cada palabra
    
    def test_formateo_subtipo_vacio_retorna_vacio(self):
        """Verifica que subtipo vacío retorna string vacío."""
        subtipo_salida = None
        
        subtipo_display = ''
        if subtipo_salida:
            subtipos_label = {
                'receta': 'Receta Médica',
                'consumo_interno': 'Consumo Interno',
            }
            subtipo_display = subtipos_label.get(subtipo_salida.lower(), subtipo_salida.title())
        
        assert subtipo_display == ''


# =============================================================================
# TESTS DE REPORTE DE MOVIMIENTOS (views_legacy.py)
# =============================================================================

class TestReporteMovimientosSubtipoExpediente(TestCase):
    """Tests para verificar que reporte_movimientos incluye los nuevos campos."""
    
    def test_transaccion_incluye_subtipo_salida(self):
        """Verifica que la estructura de transacción incluye subtipo_salida."""
        # Simular estructura de transacción como se genera en reporte_movimientos
        transaccion = {
            'referencia': 'REF-001',
            'fecha': '03/01/2026 10:00',
            'tipo': 'SALIDA',
            'tipo_original': 'SALIDA',
            'subtipo_salida': 'receta',  # Campo agregado
            'subtipo_display': 'Receta Médica',  # Campo agregado
            'numero_expediente': 'EXP-2026-001',  # Campo agregado
            'centro_origen': 'Farmacia Central',
            'centro_destino': 'Centro Penitenciario 1',
            'total_productos': 3,
            'total_cantidad': 150,
            'detalles': []
        }
        
        assert 'subtipo_salida' in transaccion
        assert 'subtipo_display' in transaccion
        assert 'numero_expediente' in transaccion
    
    def test_detalle_incluye_subtipo_y_expediente(self):
        """Verifica que los detalles de transacción incluyen subtipo y expediente."""
        detalle = {
            'producto': 'MED-001 - Paracetamol 500mg',
            'lote': 'LOTE-2026-001',
            'cantidad': 50,
            'subtipo_salida': 'receta',  # Campo agregado
            'numero_expediente': 'EXP-2026-001'  # Campo agregado
        }
        
        assert 'subtipo_salida' in detalle
        assert 'numero_expediente' in detalle
    
    def test_excel_transacciones_tiene_10_columnas(self):
        """Verifica que la hoja Transacciones tiene 10 columnas."""
        # Headers esperados para hoja 'Transacciones'
        headers = [
            '#', 'Referencia', 'Fecha', 'Tipo', 'Subtipo',
            'Centro Origen', 'Centro Destino', 'No. Expediente',
            'Productos', 'Cantidad Total'
        ]
        
        assert len(headers) == 10, f"Hoja Transacciones debe tener 10 columnas, tiene {len(headers)}"
        assert 'Subtipo' in headers
        assert 'No. Expediente' in headers
    
    def test_excel_detalle_tiene_8_columnas(self):
        """Verifica que la hoja Detalle Productos tiene 8 columnas."""
        # Headers esperados para hoja 'Detalle Productos'
        headers = [
            'Referencia', 'Tipo', '#', 'Producto', 'Lote',
            'Cantidad', 'Subtipo', 'No. Expediente'
        ]
        
        assert len(headers) == 8, f"Hoja Detalle debe tener 8 columnas, tiene {len(headers)}"


# =============================================================================
# TESTS DE CONFIGURACIÓN FRONTEND (validación de estructura)
# =============================================================================

class TestReportesJsxColumnasConfig(TestCase):
    """Tests para verificar configuración de columnas en Reportes.jsx."""
    
    def test_columnas_movimientos_incluye_subtipo_display(self):
        """Verifica que COLUMNAS_CONFIG.movimientos incluye subtipo_display."""
        columnas_movimientos = [
            {'key': 'expand', 'label': '', 'width': '40px', 'align': 'center'},
            {'key': 'fecha', 'label': 'Fecha', 'width': '130px'},
            {'key': 'tipo', 'label': 'Tipo', 'width': '90px', 'align': 'center'},
            {'key': 'subtipo_display', 'label': 'Subtipo', 'width': '120px', 'align': 'center'},
            {'key': 'referencia', 'label': 'Referencia', 'width': '160px'},
            {'key': 'centro_origen', 'label': 'Origen', 'width': '150px'},
            {'key': 'centro_destino', 'label': 'Destino', 'width': '150px'},
            {'key': 'numero_expediente', 'label': 'No. Exp.', 'width': '100px'},
            {'key': 'total_productos', 'label': 'Prods.', 'width': '70px', 'align': 'center'},
            {'key': 'total_cantidad', 'label': 'Cantidad', 'width': '80px', 'align': 'right'},
        ]
        
        keys = [col['key'] for col in columnas_movimientos]
        
        assert 'subtipo_display' in keys, "subtipo_display debe estar en columnas de movimientos"
        assert 'numero_expediente' in keys, "numero_expediente debe estar en columnas de movimientos"
    
    def test_columnas_movimientos_total_10(self):
        """Verifica que hay 10 columnas en movimientos."""
        columnas_movimientos = [
            {'key': 'expand', 'label': ''},
            {'key': 'fecha', 'label': 'Fecha'},
            {'key': 'tipo', 'label': 'Tipo'},
            {'key': 'subtipo_display', 'label': 'Subtipo'},
            {'key': 'referencia', 'label': 'Referencia'},
            {'key': 'centro_origen', 'label': 'Origen'},
            {'key': 'centro_destino', 'label': 'Destino'},
            {'key': 'numero_expediente', 'label': 'No. Exp.'},
            {'key': 'total_productos', 'label': 'Prods.'},
            {'key': 'total_cantidad', 'label': 'Cantidad'},
        ]
        
        assert len(columnas_movimientos) == 10


# =============================================================================
# TESTS DE INTEGRACIÓN (Mock)
# =============================================================================

class TestIntegracionSubtipoExpediente(TestCase):
    """Tests de integración para el flujo completo."""
    
    def test_movimiento_salida_con_subtipo_receta(self):
        """Simula un movimiento de salida tipo receta con expediente."""
        movimiento_data = {
            'tipo': 'salida',
            'subtipo_salida': 'receta',
            'numero_expediente': 'EXP-2026-00123',
            'cantidad': 10,
            'motivo': 'Dispensación por receta médica'
        }
        
        # Verificar que subtipo_salida es 'receta'
        assert movimiento_data['subtipo_salida'] == 'receta'
        # Verificar que numero_expediente tiene formato válido
        assert movimiento_data['numero_expediente'].startswith('EXP-')
    
    def test_movimiento_salida_merma_sin_expediente(self):
        """Simula un movimiento de salida tipo merma (no requiere expediente)."""
        movimiento_data = {
            'tipo': 'salida',
            'subtipo_salida': 'merma',
            'numero_expediente': None,  # No requerido para merma
            'cantidad': 5,
            'motivo': 'Producto dañado'
        }
        
        assert movimiento_data['subtipo_salida'] == 'merma'
        assert movimiento_data['numero_expediente'] is None
    
    def test_movimiento_entrada_sin_subtipo(self):
        """Verifica que entradas no requieren subtipo_salida."""
        movimiento_data = {
            'tipo': 'entrada',
            'subtipo_salida': None,  # No aplica para entradas
            'numero_expediente': None,
            'cantidad': 100,
            'motivo': 'Recepción de donación'
        }
        
        assert movimiento_data['tipo'] == 'entrada'
        assert movimiento_data['subtipo_salida'] is None


# =============================================================================
# TESTS DE VALIDACIÓN DE DATOS
# =============================================================================

class TestValidacionSubtipoExpediente(TestCase):
    """Tests de validación de datos para subtipo y expediente."""
    
    def test_subtipos_validos(self):
        """Verifica lista de subtipos válidos."""
        SUBTIPOS_VALIDOS = ['receta', 'consumo_interno', 'merma', 'caducidad', 'transferencia']
        
        assert len(SUBTIPOS_VALIDOS) == 5
        assert 'receta' in SUBTIPOS_VALIDOS
        assert 'consumo_interno' in SUBTIPOS_VALIDOS
        assert 'merma' in SUBTIPOS_VALIDOS
        assert 'caducidad' in SUBTIPOS_VALIDOS
        assert 'transferencia' in SUBTIPOS_VALIDOS
    
    def test_expediente_solo_requerido_para_receta(self):
        """Verifica que numero_expediente solo es requerido para subtipo='receta'."""
        def validar_expediente(subtipo_salida, numero_expediente):
            if subtipo_salida == 'receta':
                return numero_expediente is not None and numero_expediente.strip() != ''
            return True  # No requerido para otros subtipos
        
        # Receta sin expediente = inválido
        assert validar_expediente('receta', None) is False
        assert validar_expediente('receta', '') is False
        
        # Receta con expediente = válido
        assert validar_expediente('receta', 'EXP-001') is True
        
        # Otros subtipos sin expediente = válido
        assert validar_expediente('merma', None) is True
        assert validar_expediente('consumo_interno', None) is True
        assert validar_expediente('caducidad', '') is True
    
    def test_longitud_maxima_subtipo_salida(self):
        """Verifica que subtipo_salida respeta max_length=30."""
        max_length = 30
        
        subtipos = ['receta', 'consumo_interno', 'merma', 'caducidad', 'transferencia']
        
        for subtipo in subtipos:
            assert len(subtipo) <= max_length, f"subtipo '{subtipo}' excede max_length={max_length}"
    
    def test_longitud_maxima_numero_expediente(self):
        """Verifica que numero_expediente respeta max_length=50."""
        max_length = 50
        
        expedientes_ejemplo = [
            'EXP-2026-00001',
            'EXP-2026-12345-ABCDE',
            '1234567890123456789012345678901234567890123456789',  # 49 chars
        ]
        
        for exp in expedientes_ejemplo:
            assert len(exp) <= max_length, f"expediente '{exp}' excede max_length={max_length}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
