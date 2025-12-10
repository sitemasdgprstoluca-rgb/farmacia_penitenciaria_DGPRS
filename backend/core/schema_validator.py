"""
ISS-001 FIX (audit8): Validador de esquema para modelos unmanaged.

Este módulo verifica que las tablas unmanaged (managed=False) tengan
la estructura esperada en la base de datos, previniendo divergencias
entre el código y el esquema real.

Uso:
    from core.schema_validator import validate_unmanaged_schemas
    
    # Al inicio de la aplicación (en apps.py ready())
    validate_unmanaged_schemas()
"""
import logging
from django.db import connection
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


# Esquema esperado para tablas unmanaged
# Formato: tabla -> {columna: tipo_esperado}
EXPECTED_SCHEMAS = {
    'requisiciones': {
        'id': 'integer',
        'numero': 'character varying',
        'estado': 'character varying',
        'centro_id': 'integer',
        'solicitante_id': 'integer',
        'notas': 'text',
        'created_at': 'timestamp',
        'updated_at': 'timestamp',
        # Campos FLUJO V2
        'fecha_envio_admin': 'timestamp',
        'fecha_autorizacion_admin': 'timestamp',
        'fecha_envio_director': 'timestamp',
        'fecha_autorizacion_director': 'timestamp',
        'fecha_envio_farmacia': 'timestamp',
        'fecha_recepcion_farmacia': 'timestamp',
        'fecha_autorizacion_farmacia': 'timestamp',
        'fecha_recoleccion_limite': 'timestamp',
    },
    'requisicion_historial_estados': {
        'id': 'integer',
        'requisicion_id': 'integer',
        'estado_anterior': 'character varying',
        'estado_nuevo': 'character varying',
        'usuario_id': 'integer',
        'fecha_cambio': 'timestamp',
        'accion': 'character varying',
        'motivo': 'text',
    },
}


def get_table_columns(table_name: str) -> dict:
    """
    Obtiene las columnas de una tabla y sus tipos.
    
    Args:
        table_name: Nombre de la tabla
        
    Returns:
        dict: {nombre_columna: tipo_dato}
    """
    with connection.cursor() as cursor:
        # Query para PostgreSQL/Supabase
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, [table_name])
        
        return {row[0]: row[1] for row in cursor.fetchall()}


def validate_table_schema(table_name: str, expected_columns: dict) -> list:
    """
    Valida que una tabla tenga las columnas esperadas.
    
    Args:
        table_name: Nombre de la tabla
        expected_columns: Diccionario de columnas esperadas
        
    Returns:
        list: Lista de errores encontrados
    """
    errors = []
    
    try:
        actual_columns = get_table_columns(table_name)
        
        if not actual_columns:
            errors.append(f"Tabla '{table_name}' no existe o no tiene columnas")
            return errors
        
        # Verificar columnas faltantes
        for col_name, expected_type in expected_columns.items():
            if col_name not in actual_columns:
                errors.append(f"Columna faltante: {table_name}.{col_name}")
            else:
                actual_type = actual_columns[col_name].lower()
                expected_type_lower = expected_type.lower()
                # Verificar tipo (comparación parcial para flexibilidad)
                if not actual_type.startswith(expected_type_lower.split()[0]):
                    errors.append(
                        f"Tipo incorrecto para {table_name}.{col_name}: "
                        f"esperado '{expected_type}', actual '{actual_type}'"
                    )
                    
    except Exception as e:
        errors.append(f"Error validando tabla '{table_name}': {str(e)}")
    
    return errors


def validate_unmanaged_schemas(raise_on_error: bool = False) -> dict:
    """
    Valida todos los esquemas de tablas unmanaged.
    
    Args:
        raise_on_error: Si True, lanza excepción en caso de errores
        
    Returns:
        dict: {tabla: [errores]} para cada tabla validada
        
    Raises:
        ImproperlyConfigured: Si raise_on_error=True y hay errores
    """
    results = {}
    all_errors = []
    
    for table_name, expected_columns in EXPECTED_SCHEMAS.items():
        errors = validate_table_schema(table_name, expected_columns)
        results[table_name] = errors
        all_errors.extend(errors)
        
        if errors:
            logger.warning(
                f"ISS-001: Divergencia de esquema en tabla '{table_name}': "
                f"{len(errors)} problema(s) encontrado(s)"
            )
            for error in errors:
                logger.warning(f"  - {error}")
        else:
            logger.info(f"ISS-001: Esquema de tabla '{table_name}' verificado OK")
    
    if all_errors and raise_on_error:
        raise ImproperlyConfigured(
            f"ISS-001: Divergencia de esquema detectada en {len(all_errors)} elemento(s). "
            f"Las tablas unmanaged no coinciden con el código. "
            f"Verifique que las migraciones de Supabase estén sincronizadas."
        )
    
    return results


def check_transitions_constraint() -> bool:
    """
    Verifica que exista un CHECK constraint para estados válidos.
    
    Returns:
        bool: True si existe el constraint
    """
    from core.constants import ESTADOS_REQUISICION
    
    estados_validos = [e[0] for e in ESTADOS_REQUISICION]
    
    try:
        with connection.cursor() as cursor:
            # Verificar constraint en PostgreSQL
            cursor.execute("""
                SELECT constraint_name, check_clause
                FROM information_schema.check_constraints
                WHERE constraint_name LIKE '%requisicion%estado%'
                   OR constraint_name LIKE '%valid_estado%'
            """)
            
            constraints = cursor.fetchall()
            
            if constraints:
                logger.info(
                    f"ISS-001: CHECK constraint de estados encontrado: "
                    f"{[c[0] for c in constraints]}"
                )
                return True
            else:
                logger.warning(
                    "ISS-001: No se encontró CHECK constraint para estados de requisición. "
                    "Se recomienda agregar: CHECK (estado IN ('borrador', 'enviada', ...))"
                )
                return False
                
    except Exception as e:
        logger.warning(f"ISS-001: No se pudo verificar CHECK constraint: {e}")
        return False


# ISS-001 FIX (audit12): Validaciones adicionales de integridad
def check_foreign_key_constraints() -> dict:
    """
    ISS-001 FIX (audit12): Verifica que existan FK constraints críticas.
    
    Returns:
        dict: {constraint_name: exists}
    """
    EXPECTED_FKS = {
        'requisiciones': ['centro_id', 'solicitante_id'],
        'movimientos': ['lote_id', 'centro_id', 'requisicion_id'],
        'lotes': ['producto_id', 'centro_id'],
        'detalles_requisicion': ['requisicion_id', 'producto_id'],
    }
    
    results = {}
    
    try:
        with connection.cursor() as cursor:
            for table, expected_fks in EXPECTED_FKS.items():
                cursor.execute("""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_name = %s
                """, [table])
                
                actual_fks = {row[0] for row in cursor.fetchall()}
                
                for fk_col in expected_fks:
                    key = f"{table}.{fk_col}"
                    exists = fk_col in actual_fks
                    results[key] = exists
                    
                    if not exists:
                        logger.warning(
                            f"ISS-001 (audit12): FK faltante: {key}. "
                            "Puede causar datos huérfanos."
                        )
                    else:
                        logger.debug(f"ISS-001: FK verificada: {key}")
                        
    except Exception as e:
        logger.warning(f"ISS-001: Error verificando FKs: {e}")
    
    return results


def check_not_null_constraints() -> dict:
    """
    ISS-001 FIX (audit12): Verifica NOT NULL en columnas críticas.
    
    Returns:
        dict: {column: is_nullable}
    """
    CRITICAL_NOT_NULL = {
        'requisiciones': ['estado', 'centro_id', 'solicitante_id'],
        'movimientos': ['tipo', 'cantidad', 'lote_id'],
        'lotes': ['producto_id', 'cantidad_actual', 'estado'],
    }
    
    results = {}
    
    try:
        with connection.cursor() as cursor:
            for table, columns in CRITICAL_NOT_NULL.items():
                cursor.execute("""
                    SELECT column_name, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = %s
                        AND column_name = ANY(%s)
                """, [table, columns])
                
                for col_name, is_nullable in cursor.fetchall():
                    key = f"{table}.{col_name}"
                    results[key] = is_nullable
                    
                    if is_nullable == 'YES':
                        logger.warning(
                            f"ISS-001 (audit12): Columna crítica nullable: {key}. "
                            "Puede causar datos inconsistentes."
                        )
                        
    except Exception as e:
        logger.warning(f"ISS-001: Error verificando NOT NULL: {e}")
    
    return results


def validate_all_integrity_constraints() -> dict:
    """
    ISS-001 FIX (audit12): Ejecuta todas las validaciones de integridad.
    
    Returns:
        dict: Resumen de todas las validaciones
    """
    results = {
        'schemas': validate_unmanaged_schemas(raise_on_error=False),
        'estado_constraint': check_transitions_constraint(),
        'foreign_keys': check_foreign_key_constraints(),
        'not_null': check_not_null_constraints(),
    }
    
    # Contar problemas
    schema_errors = sum(len(errors) for errors in results['schemas'].values())
    fk_missing = sum(1 for exists in results['foreign_keys'].values() if not exists)
    nullable_critical = sum(1 for is_null in results['not_null'].values() if is_null == 'YES')
    
    total_issues = schema_errors + fk_missing + nullable_critical
    if not results['estado_constraint']:
        total_issues += 1
    
    if total_issues > 0:
        logger.warning(
            f"ISS-001 (audit12): Validación de integridad completada con "
            f"{total_issues} problema(s). Verifique el esquema de Supabase."
        )
    else:
        logger.info("ISS-001 (audit12): Validación de integridad completada OK")
    
    results['total_issues'] = total_issues
    return results
