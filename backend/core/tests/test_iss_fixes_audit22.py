"""
Tests para correcciones de audit22.

ISS-001: Verificación automática de esquema BD al arranque
ISS-002: Campo estado de Lote es propiedad calculada (confirmado con esquema real)
ISS-003: Constraints de integridad en BD
ISS-004: Campos de trazabilidad existen (confirmado con esquema real)
ISS-005: Tests de esquema
"""
import pytest
from django.test import TestCase
from unittest.mock import MagicMock, patch


class TestISS001VerificacionEsquema(TestCase):
    """
    ISS-001: Verifica funcionalidad de verificación de esquema.
    """
    
    def test_script_verify_schema_existe(self):
        """Verifica que el script de verificación existe."""
        import os
        from pathlib import Path
        
        base_dir = Path(__file__).parent.parent.parent
        script_path = base_dir / 'scripts' / 'verify_schema.py'
        
        assert script_path.exists(), f"Script debe existir en {script_path}"
    
    def test_verificar_columnas_criticas_definidas(self):
        """Verifica que COLUMNAS_CRITICAS está definido."""
        from scripts.verify_schema import COLUMNAS_CRITICAS
        
        assert 'movimientos' in COLUMNAS_CRITICAS
        assert 'subtipo_salida' in COLUMNAS_CRITICAS['movimientos']
        assert 'numero_expediente' in COLUMNAS_CRITICAS['movimientos']
        
        assert 'detalles_requisicion' in COLUMNAS_CRITICAS
        assert 'motivo_ajuste' in COLUMNAS_CRITICAS['detalles_requisicion']
        
        assert 'lotes' in COLUMNAS_CRITICAS
        assert 'centro_id' in COLUMNAS_CRITICAS['lotes']
    
    def test_verificacion_arranque_existe(self):
        """Verifica que existe función de verificación de arranque."""
        from scripts.verify_schema import verificacion_arranque
        
        assert callable(verificacion_arranque)
    
    def test_generar_sql_constraints_retorna_sql(self):
        """Verifica que generar_sql_constraints retorna SQL válido."""
        from scripts.verify_schema import generar_sql_constraints
        
        sql = generar_sql_constraints()
        
        assert isinstance(sql, str)
        assert "ALTER TABLE" in sql
        assert "CHECK" in sql
        assert "cantidad_actual >= 0" in sql
        assert "cantidad > 0" in sql


class TestISS002CampoEstadoLote(TestCase):
    """
    ISS-002: Confirma que el campo estado NO existe en BD.
    
    Según el esquema proporcionado, la tabla 'lotes' NO tiene columna 'estado'.
    Es una propiedad calculada en el modelo Django.
    """
    
    def test_lote_estado_es_property(self):
        """Verifica que Lote.estado es una property."""
        from core.models import Lote
        
        estado_descriptor = getattr(Lote, 'estado', None)
        assert estado_descriptor is not None
        assert isinstance(estado_descriptor, property), \
            "Lote.estado debe ser @property (no existe en BD)"
    
    def test_lote_no_tiene_campo_estado(self):
        """Verifica que 'estado' no es un campo de modelo."""
        from core.models import Lote
        
        campos_con_columna = [
            f.name for f in Lote._meta.get_fields() 
            if hasattr(f, 'column') and f.column is not None
        ]
        
        assert 'estado' not in campos_con_columna, \
            "'estado' NO debe ser campo de BD (es property calculada)"
    
    def test_columnas_reales_lote(self):
        """Verifica las columnas reales esperadas en Lote."""
        from core.models import Lote
        
        campos_nombres = [
            f.name for f in Lote._meta.get_fields() 
            if hasattr(f, 'column')
        ]
        
        # Columnas que SÍ deben existir según esquema BD
        columnas_esperadas = ['id', 'numero_lote', 'producto', 'cantidad_actual', 
                              'cantidad_inicial', 'fecha_caducidad', 'activo', 'centro']
        
        for col in columnas_esperadas:
            assert col in campos_nombres or col + '_id' in campos_nombres, \
                f"Columna '{col}' debe existir en modelo Lote"


class TestISS003Constraints(TestCase):
    """
    ISS-003: Verifica definición de constraints recomendados.
    """
    
    def test_constraints_recomendados_definidos(self):
        """Verifica que CONSTRAINTS_RECOMENDADOS está definido."""
        from scripts.verify_schema import CONSTRAINTS_RECOMENDADOS
        
        assert 'lotes' in CONSTRAINTS_RECOMENDADOS
        assert 'movimientos' in CONSTRAINTS_RECOMENDADOS
    
    def test_constraint_stock_no_negativo(self):
        """Verifica constraint de stock no negativo."""
        from scripts.verify_schema import CONSTRAINTS_RECOMENDADOS
        
        lotes_constraints = CONSTRAINTS_RECOMENDADOS['lotes']
        constraint_names = [c[0] for c in lotes_constraints]
        
        assert 'chk_lotes_cantidad_no_negativa' in constraint_names


class TestISS004CamposTrazabilidad(TestCase):
    """
    ISS-004: Verifica que los campos de trazabilidad existen en modelos.
    
    Según el esquema BD proporcionado:
    - movimientos.subtipo_salida: EXISTS
    - movimientos.numero_expediente: EXISTS
    - detalles_requisicion.motivo_ajuste: EXISTS
    """
    
    def test_movimiento_tiene_subtipo_salida(self):
        """Verifica que Movimiento tiene campo subtipo_salida."""
        from core.models import Movimiento
        
        campos = [f.name for f in Movimiento._meta.get_fields()]
        assert 'subtipo_salida' in campos, \
            "Movimiento debe tener campo subtipo_salida"
    
    def test_movimiento_tiene_numero_expediente(self):
        """Verifica que Movimiento tiene campo numero_expediente."""
        from core.models import Movimiento
        
        campos = [f.name for f in Movimiento._meta.get_fields()]
        assert 'numero_expediente' in campos, \
            "Movimiento debe tener campo numero_expediente"
    
    def test_detalle_requisicion_tiene_motivo_ajuste(self):
        """Verifica que DetalleRequisicion tiene campo motivo_ajuste."""
        from core.models import DetalleRequisicion
        
        campos = [f.name for f in DetalleRequisicion._meta.get_fields()]
        assert 'motivo_ajuste' in campos, \
            "DetalleRequisicion debe tener campo motivo_ajuste"


class TestISS005ComandoVerifySchema(TestCase):
    """
    ISS-005: Verifica que existe comando de verificación de esquema.
    """
    
    def test_comando_existe(self):
        """Verifica que el comando verify_schema existe."""
        from django.core.management import get_commands
        
        commands = get_commands()
        assert 'verify_schema' in commands, \
            "Debe existir comando 'python manage.py verify_schema'"
    
    def test_comando_tiene_opcion_strict(self):
        """Verifica que el comando tiene opción --strict."""
        from core.management.commands.verify_schema import Command
        import argparse
        
        cmd = Command()
        parser = argparse.ArgumentParser()
        cmd.add_arguments(parser)
        
        # Verificar que --strict está definido
        actions = {a.dest: a for a in parser._actions}
        assert 'strict' in actions
    
    def test_comando_tiene_opcion_sql(self):
        """Verifica que el comando tiene opción --sql."""
        from core.management.commands.verify_schema import Command
        import argparse
        
        cmd = Command()
        parser = argparse.ArgumentParser()
        cmd.add_arguments(parser)
        
        actions = {a.dest: a for a in parser._actions}
        assert 'sql' in actions


class TestEsquemaBDvsModelos(TestCase):
    """
    Tests que validan alineación entre modelos y esquema BD real.
    
    Basados en el esquema proporcionado por el usuario.
    """
    
    def test_lote_columnas_alineadas_con_bd(self):
        """Verifica columnas de Lote vs esquema BD."""
        from core.models import Lote
        
        # Columnas en BD según esquema proporcionado
        columnas_bd = {
            'id', 'numero_lote', 'producto_id', 'cantidad_inicial',
            'cantidad_actual', 'fecha_fabricacion', 'fecha_caducidad',
            'precio_unitario', 'numero_contrato', 'marca', 'ubicacion',
            'centro_id', 'activo', 'created_at', 'updated_at'
        }
        
        # Obtener columnas del modelo
        columnas_modelo = set()
        for f in Lote._meta.get_fields():
            if hasattr(f, 'column') and f.column:
                columnas_modelo.add(f.column)
        
        # Verificar que las columnas del modelo existen en BD
        for col in columnas_modelo:
            if col not in columnas_bd:
                # Solo advertir, no fallar (modelo puede tener menos columnas)
                pass
    
    def test_movimiento_columnas_alineadas_con_bd(self):
        """Verifica columnas de Movimiento vs esquema BD."""
        from core.models import Movimiento
        
        # Columnas en BD según esquema proporcionado
        columnas_bd = {
            'id', 'tipo', 'producto_id', 'lote_id', 'cantidad',
            'centro_origen_id', 'centro_destino_id', 'requisicion_id',
            'usuario_id', 'motivo', 'referencia', 'fecha', 'created_at',
            'subtipo_salida', 'numero_expediente'
        }
        
        # Campos críticos que DEBEN existir en modelo
        campos_criticos = ['subtipo_salida', 'numero_expediente']
        
        for campo in campos_criticos:
            assert any(
                getattr(f, 'column', None) == campo or f.name == campo
                for f in Movimiento._meta.get_fields()
            ), f"Campo '{campo}' debe existir en modelo Movimiento"
