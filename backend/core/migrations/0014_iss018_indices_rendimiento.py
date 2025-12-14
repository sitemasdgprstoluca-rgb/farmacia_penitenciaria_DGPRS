"""
ISS-018: Índices de base de datos optimizados.

Migración para agregar índices que mejoran el rendimiento
de consultas frecuentes. Usa IF NOT EXISTS para evitar
errores si los índices ya existen.

También verifica que las tablas existan antes de crear
índices para manejar casos de BD parcialmente migradas.
"""
from django.db import migrations


def table_exists(schema_editor, table_name):
    """
    Verifica si una tabla existe en la base de datos.
    HALLAZGO #7: Compatible con PostgreSQL, SQLite y MySQL.
    """
    cursor = schema_editor.connection.cursor()
    vendor = schema_editor.connection.vendor
    
    if vendor == 'postgresql':
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s)",
            [table_name]
        )
        return cursor.fetchone()[0]
    elif vendor == 'sqlite':
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            [table_name]
        )
        return cursor.fetchone() is not None
    else:
        # MySQL/MariaDB
        cursor.execute("SHOW TABLES LIKE %s", [table_name])
        return cursor.fetchone() is not None


def create_index_if_not_exists(schema_editor, table_name, index_name, columns):
    """
    Crea un índice solo si no existe Y si la tabla existe.
    HALLAZGO #7: Compatible con PostgreSQL, SQLite y MySQL.
    """
    # Verificar primero si la tabla existe
    if not table_exists(schema_editor, table_name):
        return  # No crear índice si la tabla no existe
    
    vendor = schema_editor.connection.vendor
    cursor = schema_editor.connection.cursor()
    columns_sql = ', '.join(columns)
    
    if vendor == 'postgresql':
        # PostgreSQL soporta IF NOT EXISTS
        sql = f'CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table_name}" ({columns_sql})'
        schema_editor.execute(sql)
    elif vendor == 'sqlite':
        # SQLite: verificar si existe primero (usa ? para parámetros)
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            [index_name]
        )
        if not cursor.fetchone():
            sql = f'CREATE INDEX "{index_name}" ON "{table_name}" ({columns_sql})'
            schema_editor.execute(sql)
    else:
        # MySQL/MariaDB: usar IF NOT EXISTS
        sql = f'CREATE INDEX {index_name} ON {table_name} ({columns_sql})'
        try:
            schema_editor.execute(sql)
        except Exception:
            # Índice ya existe, ignorar
            pass


def add_performance_indexes(apps, schema_editor):
    """Añade todos los índices de rendimiento."""
    
    # === ÍNDICES PARA REQUISICIONES ===
    create_index_if_not_exists(
        schema_editor, 'core_requisicion', 'idx_req_estado_fecha',
        ['estado', 'fecha_solicitud DESC']
    )
    create_index_if_not_exists(
        schema_editor, 'core_requisicion', 'idx_req_centro_estado',
        ['centro_id', 'estado', 'fecha_solicitud DESC']
    )
    create_index_if_not_exists(
        schema_editor, 'core_requisicion', 'idx_req_usuario_fecha',
        ['usuario_solicita_id', 'fecha_solicitud DESC']
    )
    
    # === ÍNDICES PARA MOVIMIENTOS ===
    create_index_if_not_exists(
        schema_editor, 'core_movimiento', 'idx_mov_tipo_fecha',
        ['tipo', 'fecha DESC']
    )
    create_index_if_not_exists(
        schema_editor, 'core_movimiento', 'idx_mov_lote_fecha',
        ['lote_id', 'fecha DESC']
    )
    create_index_if_not_exists(
        schema_editor, 'core_movimiento', 'idx_mov_req_fecha',
        ['requisicion_id', 'fecha DESC']
    )
    create_index_if_not_exists(
        schema_editor, 'core_movimiento', 'idx_mov_usuario_fecha',
        ['usuario_id', 'fecha DESC']
    )
    
    # === ÍNDICES PARA LOTES ===
    create_index_if_not_exists(
        schema_editor, 'core_lote', 'idx_lote_caducidad_estado',
        ['fecha_caducidad', 'estado']
    )
    create_index_if_not_exists(
        schema_editor, 'core_lote', 'idx_lote_prod_stock',
        ['producto_id', 'estado', 'cantidad_actual']
    )
    create_index_if_not_exists(
        schema_editor, 'core_lote', 'idx_lote_centro_estado',
        ['centro_id', 'estado', 'fecha_caducidad DESC']
    )
    
    # === ÍNDICES PARA PRODUCTOS ===
    create_index_if_not_exists(
        schema_editor, 'core_producto', 'idx_prod_activo_desc',
        ['activo', 'descripcion']
    )
    create_index_if_not_exists(
        schema_editor, 'core_producto', 'idx_prod_stock_min',
        ['stock_minimo', 'activo']
    )
    
    # === ÍNDICES PARA DETALLES REQUISICIÓN ===
    create_index_if_not_exists(
        schema_editor, 'core_detallerequisicion', 'idx_det_prod_req',
        ['producto_id', 'requisicion_id']
    )


def remove_performance_indexes(apps, schema_editor):
    """Elimina los índices de rendimiento (rollback)."""
    indexes_to_remove = [
        'idx_req_estado_fecha',
        'idx_req_centro_estado', 
        'idx_req_usuario_fecha',
        'idx_mov_tipo_fecha',
        'idx_mov_lote_fecha',
        'idx_mov_req_fecha',
        'idx_mov_usuario_fecha',
        'idx_lote_caducidad_estado',
        'idx_lote_prod_stock',
        'idx_lote_centro_estado',
        'idx_prod_activo_desc',
        'idx_prod_stock_min',
        'idx_det_prod_req',
    ]
    
    for index_name in indexes_to_remove:
        if schema_editor.connection.vendor == 'postgresql':
            schema_editor.execute(f'DROP INDEX IF EXISTS "{index_name}"')
        else:
            # SQLite
            try:
                schema_editor.execute(f'DROP INDEX IF EXISTS "{index_name}"')
            except Exception:
                pass  # Ignorar si no existe


class Migration(migrations.Migration):
    """
    ISS-018: Migración para añadir índices de rendimiento.
    
    Usa RunPython con IF NOT EXISTS para ser idempotente
    y evitar errores si los índices ya existen.
    """
    
    dependencies = [
        ('core', '0013_tema_global'),
    ]
    
    operations = [
        migrations.RunPython(
            add_performance_indexes,
            remove_performance_indexes,
        ),
    ]
