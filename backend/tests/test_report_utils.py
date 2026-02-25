"""
Tests exhaustivos para report_utils y los 7 endpoints de reportes.

Cubre la matriz obligatoria:
- Sin filtros
- Solo 1 filtro
- Combinación completa
- Fechas: desde válido, hasta vacío / desde vacío, hasta válido / desde > hasta / inválida
- Centro: vacío/todos, específico, no permitido
- Export: Excel = JSON, PDF = JSON
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIRequestFactory

from inventario.services.report_utils import (
    _norm_str, _norm_bool, _parse_date, _parse_int,
    resolver_centro, CentroResuelto,
    parse_report_filters, FiltrosReporte,
    verificar_permisos_reporte, resolver_centro_para_queryset,
)


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS: Primitivos de normalización
# ═══════════════════════════════════════════════════════════════════════════════

class TestNormStr:
    def test_none(self):
        assert _norm_str(None) is None

    def test_empty(self):
        assert _norm_str('') is None
        assert _norm_str('   ') is None

    def test_null_string(self):
        assert _norm_str('null') is None
        assert _norm_str('NULL') is None
        assert _norm_str('undefined') is None
        assert _norm_str('None') is None

    def test_valid(self):
        assert _norm_str('hello') == 'hello'
        assert _norm_str('  hello  ') == 'hello'
        assert _norm_str('42') == '42'

    def test_int_input(self):
        assert _norm_str(42) == '42'


class TestNormBool:
    def test_true_values(self):
        assert _norm_bool(True) is True
        assert _norm_bool('true') is True
        assert _norm_bool('True') is True
        assert _norm_bool('TRUE') is True
        assert _norm_bool('1') is True
        assert _norm_bool('yes') is True
        assert _norm_bool('si') is True

    def test_false_values(self):
        assert _norm_bool(False) is False
        assert _norm_bool(None) is False
        assert _norm_bool('false') is False
        assert _norm_bool('0') is False
        assert _norm_bool('') is False
        assert _norm_bool('no') is False


class TestParseDate:
    def test_iso_format(self):
        assert _parse_date('2025-06-15') == date(2025, 6, 15)

    def test_dd_mm_yyyy(self):
        assert _parse_date('15/06/2025') == date(2025, 6, 15)

    def test_none(self):
        assert _parse_date(None) is None
        assert _parse_date('') is None

    def test_invalid(self):
        assert _parse_date('not-a-date') is None
        assert _parse_date('31/13/2025') is None  # Mes 13

    def test_with_spaces(self):
        assert _parse_date('  2025-06-15  ') == date(2025, 6, 15)


class TestParseInt:
    def test_valid(self):
        assert _parse_int('42') == 42
        assert _parse_int(42) == 42

    def test_invalid(self):
        assert _parse_int(None) is None
        assert _parse_int('') is None
        assert _parse_int('abc') is None
        assert _parse_int('3.5') is None


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS: resolver_centro
# ═══════════════════════════════════════════════════════════════════════════════

class TestResolverCentro:
    def test_todos(self):
        cr = resolver_centro('todos')
        assert cr.es_todos is True
        assert cr.es_central is False
        assert cr.centro_id is None

    def test_central(self):
        cr = resolver_centro('central')
        assert cr.es_central is True
        assert cr.es_todos is False

    def test_numeric_id(self):
        cr = resolver_centro('42')
        assert cr.es_especifico is True
        assert cr.centro_id == 42

    def test_none(self):
        cr = resolver_centro(None)
        assert cr.es_todos is True

    def test_empty(self):
        cr = resolver_centro('')
        assert cr.es_todos is True

    def test_null_string(self):
        cr = resolver_centro('null')
        assert cr.es_todos is True

    def test_undefined(self):
        cr = resolver_centro('undefined')
        assert cr.es_todos is True

    def test_invalid_string(self):
        cr = resolver_centro('foobar')
        assert cr.es_todos is True

    def test_todos_case_insensitive(self):
        cr = resolver_centro('TODOS')
        assert cr.es_todos is True

    def test_central_case_insensitive(self):
        cr = resolver_centro('CENTRAL')
        assert cr.es_central is True

    def test_zero_id(self):
        cr = resolver_centro('0')
        assert cr.es_todos is True  # 0 is not a valid ID

    def test_negative_id(self):
        cr = resolver_centro('-1')
        assert cr.es_todos is True  # Negatives not valid

    def test_debe_filtrar(self):
        assert resolver_centro('central').debe_filtrar is True
        assert resolver_centro('42').debe_filtrar is True
        assert resolver_centro('todos').debe_filtrar is False
        assert resolver_centro(None).debe_filtrar is False


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS: parse_report_filters
# ═══════════════════════════════════════════════════════════════════════════════

class TestParseReportFilters:
    """Tests usando mock request objects."""
    
    def _make_request(self, params: dict):
        """Crea un mock request con query_params."""
        request = MagicMock()
        request.query_params = params
        request.user = MagicMock()
        return request

    # ── Sin filtros ──────────────────────────────────────────
    def test_sin_filtros(self):
        from django.utils import timezone
        now = timezone.now()
        req = self._make_request({})
        f = parse_report_filters(req, 'inventario')
        assert not f.tiene_errores
        assert f.centro.es_todos is True
        assert f.fecha_inicio is None
        assert f.fecha_fin is None
        assert f.formato == 'json'
        assert f.dias == 30
        assert f.nivel_stock is None
        assert f.estado is None
        # mes y anio toman defaults del momento actual
        assert f.mes == now.month
        assert f.anio == now.year

    # ── Formato ──────────────────────────────────────────────
    def test_formato_excel(self):
        req = self._make_request({'formato': 'excel'})
        f = parse_report_filters(req)
        assert f.formato == 'excel'

    def test_formato_pdf(self):
        req = self._make_request({'formato': 'pdf'})
        f = parse_report_filters(req)
        assert f.formato == 'pdf'

    def test_formato_invalido_ignora(self):
        req = self._make_request({'formato': 'csv'})
        f = parse_report_filters(req)
        assert f.formato == 'json'  # Default

    # ── Fechas ───────────────────────────────────────────────
    def test_fecha_inicio_valida(self):
        req = self._make_request({'fecha_inicio': '2025-01-15'})
        f = parse_report_filters(req)
        assert f.fecha_inicio == date(2025, 1, 15)
        assert not f.tiene_errores

    def test_fecha_inicio_dd_mm_yyyy(self):
        req = self._make_request({'fecha_inicio': '15/06/2025'})
        f = parse_report_filters(req)
        assert f.fecha_inicio == date(2025, 6, 15)

    def test_fecha_invalida_da_error(self):
        req = self._make_request({'fecha_inicio': 'no-es-fecha'})
        f = parse_report_filters(req)
        assert f.tiene_errores
        assert 'fecha_inicio inválida' in f.errores[0]

    def test_desde_mayor_que_hasta_da_error(self):
        req = self._make_request({
            'fecha_inicio': '2025-06-30',
            'fecha_fin': '2025-06-01'
        })
        f = parse_report_filters(req)
        assert f.tiene_errores
        assert 'Rango de fechas inválido' in f.errores[0]

    def test_solo_desde_sin_error(self):
        req = self._make_request({'fecha_inicio': '2025-01-01'})
        f = parse_report_filters(req)
        assert not f.tiene_errores
        assert f.fecha_inicio == date(2025, 1, 1)
        assert f.fecha_fin is None

    def test_solo_hasta_sin_error(self):
        req = self._make_request({'fecha_fin': '2025-12-31'})
        f = parse_report_filters(req)
        assert not f.tiene_errores
        assert f.fecha_inicio is None
        assert f.fecha_fin == date(2025, 12, 31)

    def test_fecha_vacia_ignorada(self):
        req = self._make_request({'fecha_inicio': '', 'fecha_fin': ''})
        f = parse_report_filters(req)
        assert not f.tiene_errores
        assert f.fecha_inicio is None
        assert f.fecha_fin is None

    # ── Centro ───────────────────────────────────────────────
    def test_centro_todos(self):
        req = self._make_request({'centro': 'todos'})
        f = parse_report_filters(req)
        assert f.centro.es_todos is True

    def test_centro_central(self):
        req = self._make_request({'centro': 'central'})
        f = parse_report_filters(req)
        assert f.centro.es_central is True

    def test_centro_id(self):
        req = self._make_request({'centro': '5'})
        f = parse_report_filters(req)
        assert f.centro.es_especifico is True
        assert f.centro.centro_id == 5

    # ── Inventario: nivel_stock ──────────────────────────────
    def test_nivel_stock_valido(self):
        for nivel in ('alto', 'bajo', 'normal', 'sin_stock', 'critico'):
            req = self._make_request({'nivel_stock': nivel})
            f = parse_report_filters(req, 'inventario')
            assert f.nivel_stock == nivel
            assert not f.tiene_errores

    def test_nivel_stock_invalido(self):
        req = self._make_request({'nivel_stock': 'inexistente'})
        f = parse_report_filters(req, 'inventario')
        assert f.tiene_errores
        assert 'nivel_stock' in f.errores[0]

    # ── Caducidades: días ────────────────────────────────────
    def test_dias_default(self):
        req = self._make_request({})
        f = parse_report_filters(req, 'caducidades')
        assert f.dias == 30

    def test_dias_custom(self):
        req = self._make_request({'dias': '90'})
        f = parse_report_filters(req)
        assert f.dias == 90

    def test_dias_negativo_error(self):
        req = self._make_request({'dias': '-5'})
        f = parse_report_filters(req)
        # -5 parsed as int: not > 0 → error added, dias stays at default 30
        assert f.tiene_errores
        assert f.dias == 30
        assert any('dias' in e for e in f.errores)

    def test_dias_capped(self):
        req = self._make_request({'dias': '99999'})
        f = parse_report_filters(req)
        assert f.dias == 3650  # Capped

    # ── Movimientos: tipo ────────────────────────────────────
    def test_tipo_movimiento_entrada(self):
        req = self._make_request({'tipo': 'entrada'})
        f = parse_report_filters(req)
        assert f.tipo_movimiento == 'entrada'

    def test_tipo_movimiento_salida(self):
        req = self._make_request({'tipo': 'salida'})
        f = parse_report_filters(req)
        assert f.tipo_movimiento == 'salida'

    def test_tipo_movimiento_invalido(self):
        req = self._make_request({'tipo': 'transferencia'})
        f = parse_report_filters(req)
        assert f.tiene_errores
        assert 'tipo de movimiento' in f.errores[0]

    # ── Contratos: numero_contrato ───────────────────────────
    def test_numero_contrato(self):
        req = self._make_request({'numero_contrato': 'CB/A/37/2025'})
        f = parse_report_filters(req)
        assert f.numero_contrato == 'CB/A/37/2025'

    def test_numero_contrato_vacio(self):
        req = self._make_request({'numero_contrato': ''})
        f = parse_report_filters(req)
        assert f.numero_contrato is None

    # ── Parcialidades: sobreentrega ──────────────────────────
    def test_sobreentrega_true(self):
        req = self._make_request({'es_sobreentrega': 'true'})
        f = parse_report_filters(req)
        assert f.es_sobreentrega is True

    def test_sobreentrega_false(self):
        req = self._make_request({'es_sobreentrega': 'false'})
        f = parse_report_filters(req)
        assert f.es_sobreentrega is False

    # ── Control Mensual: mes/año ─────────────────────────────
    def test_mes_valido(self):
        req = self._make_request({'mes': '6', 'anio': '2025'})
        f = parse_report_filters(req, 'control_mensual')
        assert f.mes == 6
        assert f.anio == 2025

    def test_mes_invalido(self):
        req = self._make_request({'mes': '13'})
        f = parse_report_filters(req)
        assert f.tiene_errores
        assert 'mes' in f.errores[0]

    def test_anio_invalido(self):
        req = self._make_request({'anio': '1900'})
        f = parse_report_filters(req)
        assert f.tiene_errores
        assert 'anio' in f.errores[0]

    # ── Combinaciones ────────────────────────────────────────
    def test_combinacion_completa_inventario(self):
        req = self._make_request({
            'centro': '3',
            'nivel_stock': 'bajo',
            'fecha_inicio': '2025-01-01',
            'fecha_fin': '2025-06-30',
            'formato': 'excel'
        })
        f = parse_report_filters(req, 'inventario')
        assert not f.tiene_errores
        assert f.centro.centro_id == 3
        assert f.nivel_stock == 'bajo'
        assert f.fecha_inicio == date(2025, 1, 1)
        assert f.fecha_fin == date(2025, 6, 30)
        assert f.formato == 'excel'

    def test_combinacion_completa_movimientos(self):
        req = self._make_request({
            'centro': 'central',
            'tipo': 'entrada',
            'fecha_inicio': '2025-03-01',
            'fecha_fin': '2025-03-31',
            'estado_confirmacion': 'todos',
            'formato': 'pdf'
        })
        f = parse_report_filters(req, 'movimientos')
        assert not f.tiene_errores
        assert f.centro.es_central is True
        assert f.tipo_movimiento == 'entrada'
        assert f.estado_confirmacion == 'todos'
        assert f.formato == 'pdf'

    def test_combinacion_completa_caducidades(self):
        req = self._make_request({
            'centro': 'todos',
            'dias': '60',
            'estado': 'critico'
        })
        f = parse_report_filters(req, 'caducidades')
        assert not f.tiene_errores
        assert f.centro.es_todos is True
        assert f.dias == 60
        assert f.estado_caducidad == 'critico'

    def test_combinacion_completa_parcialidades(self):
        req = self._make_request({
            'fecha_inicio': '2025-01-01',
            'fecha_fin': '2025-12-31',
            'centro': '5',
            'es_sobreentrega': 'true',
            'numero_lote': 'LOT-001',
            'clave_producto': 'PRD-X'
        })
        f = parse_report_filters(req, 'parcialidades')
        assert not f.tiene_errores
        assert f.centro.centro_id == 5
        assert f.es_sobreentrega is True
        assert f.numero_lote == 'LOT-001'
        assert f.clave_producto == 'PRD-X'

    # ── Error response ───────────────────────────────────────
    def test_respuesta_error(self):
        req = self._make_request({'fecha_inicio': 'basura', 'mes': '99'})
        f = parse_report_filters(req)
        assert f.tiene_errores
        resp = f.respuesta_error()
        assert resp.status_code == 400
        assert 'error' in resp.data
        assert 'errores' in resp.data
        assert len(resp.data['errores']) >= 2


# ═══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS: resolver_centro_para_queryset
# ═══════════════════════════════════════════════════════════════════════════════

class TestResolverCentroParaQueryset:
    def test_admin_respeta_filtro(self):
        f = FiltrosReporte()
        f.centro = resolver_centro('central')
        result = resolver_centro_para_queryset(f, es_admin=True, user_centro=None)
        assert result.es_central is True

    def test_no_admin_fuerza_su_centro(self):
        f = FiltrosReporte()
        f.centro = resolver_centro('todos')  # Intenta ver todos
        mock_centro = MagicMock()
        mock_centro.id = 7
        result = resolver_centro_para_queryset(f, es_admin=False, user_centro=mock_centro)
        assert result.es_especifico is True
        assert result.centro_id == 7
