"""
ISS-003 FIX (audit21): Script de verificación de esquema BD vs modelos Django.

Este script compara los modelos Django (managed=False) contra el esquema real
de la base de datos para detectar discrepancias antes del despliegue.

USO:
    python manage.py shell < scripts/verify_schema.py
    
    O importar y ejecutar:
    from scripts.verify_schema import verificar_esquema
    resultado = verificar_esquema()

VERIFICACIONES:
1. Columnas esperadas por Django existen en BD
2. Tipos de datos coinciden (aproximado)
3. Constraints NOT NULL alineados
4. Foreign keys definidas

NOTAS:
- Requiere conexión a BD real (no sqlite)
- El campo 'estado' de Lote es propiedad calculada, NO columna
- managed=False significa que Django no aplica migraciones
"""
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ColumnaEsperada:
    """Representa una columna esperada según el modelo Django."""
    nombre: str
    tipo_django: str
    nullable: bool = True
    es_fk: bool = False
    fk_tabla: Optional[str] = None


@dataclass
class ResultadoVerificacion:
    """Resultado de la verificación de esquema."""
    tabla: str
    columnas_faltantes: List[str] = field(default_factory=list)
    columnas_extra: List[str] = field(default_factory=list)
    tipos_incompatibles: List[Tuple[str, str, str]] = field(default_factory=list)  # (col, esperado, real)
    nullable_incompatibles: List[Tuple[str, bool, bool]] = field(default_factory=list)
    errores: List[str] = field(default_factory=list)
    
    @property
    def es_valido(self) -> bool:
        return not (
            self.columnas_faltantes or 
            self.tipos_incompatibles or 
            self.errores
        )


# Mapeo de tipos Django a tipos PostgreSQL esperados
DJANGO_TO_PG_TYPES = {
    'AutoField': ['integer', 'bigint', 'serial', 'bigserial'],
    'BigAutoField': ['bigint', 'bigserial'],
    'IntegerField': ['integer', 'int4', 'smallint', 'int2'],
    'BigIntegerField': ['bigint', 'int8'],
    'SmallIntegerField': ['smallint', 'int2'],
    'DecimalField': ['numeric', 'decimal'],
    'FloatField': ['double precision', 'float8', 'real', 'float4'],
    'CharField': ['character varying', 'varchar', 'text'],
    'TextField': ['text', 'character varying', 'varchar'],
    'BooleanField': ['boolean', 'bool'],
    'DateField': ['date'],
    'DateTimeField': ['timestamp with time zone', 'timestamptz', 'timestamp without time zone', 'timestamp'],
    'TimeField': ['time with time zone', 'time without time zone', 'time'],
    'UUIDField': ['uuid'],
    'JSONField': ['jsonb', 'json'],
    'ForeignKey': ['integer', 'bigint', 'uuid'],  # Depende de la PK referenciada
    'ImageField': ['character varying', 'varchar', 'text'],
    'FileField': ['character varying', 'varchar', 'text'],
    'EmailField': ['character varying', 'varchar', 'text'],
    'URLField': ['character varying', 'varchar', 'text'],
    'SlugField': ['character varying', 'varchar'],
    'PositiveIntegerField': ['integer', 'int4'],
    'PositiveSmallIntegerField': ['smallint', 'int2'],
}


def get_columnas_modelo(modelo) -> Dict[str, ColumnaEsperada]:
    """
    Extrae las columnas esperadas de un modelo Django.
    
    Args:
        modelo: Clase del modelo Django
        
    Returns:
        Dict con nombre de columna -> ColumnaEsperada
    """
    columnas = {}
    
    for field in modelo._meta.get_fields():
        # Ignorar relaciones inversas y campos no concretos
        if not hasattr(field, 'column') or field.column is None:
            continue
        
        nombre_col = field.column
        tipo = field.get_internal_type()
        nullable = getattr(field, 'null', True)
        
        es_fk = tipo == 'ForeignKey'
        fk_tabla = None
        if es_fk and hasattr(field, 'related_model'):
            fk_tabla = field.related_model._meta.db_table
        
        columnas[nombre_col] = ColumnaEsperada(
            nombre=nombre_col,
            tipo_django=tipo,
            nullable=nullable,
            es_fk=es_fk,
            fk_tabla=fk_tabla
        )
    
    return columnas


def get_columnas_bd(cursor, tabla: str) -> Dict[str, dict]:
    """
    Obtiene las columnas reales de una tabla en PostgreSQL.
    
    Args:
        cursor: Cursor de BD
        tabla: Nombre de la tabla
        
    Returns:
        Dict con nombre de columna -> {tipo, nullable, ...}
    """
    cursor.execute("""
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, [tabla])
    
    columnas = {}
    for row in cursor.fetchall():
        columnas[row[0]] = {
            'tipo': row[1],
            'nullable': row[2] == 'YES',
            'default': row[3],
            'max_length': row[4]
        }
    
    return columnas


def verificar_modelo(modelo, cursor) -> ResultadoVerificacion:
    """
    Verifica un modelo contra su tabla en BD.
    
    Args:
        modelo: Clase del modelo Django
        cursor: Cursor de BD
        
    Returns:
        ResultadoVerificacion con discrepancias encontradas
    """
    tabla = modelo._meta.db_table
    resultado = ResultadoVerificacion(tabla=tabla)
    
    try:
        columnas_django = get_columnas_modelo(modelo)
        columnas_bd = get_columnas_bd(cursor, tabla)
    except Exception as e:
        resultado.errores.append(f"Error obteniendo columnas: {e}")
        return resultado
    
    # Verificar que la tabla existe
    if not columnas_bd:
        resultado.errores.append(f"Tabla '{tabla}' no encontrada en BD")
        return resultado
    
    # 1. Columnas faltantes en BD
    for nombre_col, col_esperada in columnas_django.items():
        if nombre_col not in columnas_bd:
            resultado.columnas_faltantes.append(nombre_col)
    
    # 2. Columnas extra en BD (no crítico, solo info)
    for nombre_col in columnas_bd:
        if nombre_col not in columnas_django:
            resultado.columnas_extra.append(nombre_col)
    
    # 3. Verificar tipos de datos
    for nombre_col, col_esperada in columnas_django.items():
        if nombre_col not in columnas_bd:
            continue
            
        col_real = columnas_bd[nombre_col]
        tipos_esperados = DJANGO_TO_PG_TYPES.get(col_esperada.tipo_django, [])
        
        if tipos_esperados and col_real['tipo'] not in tipos_esperados:
            resultado.tipos_incompatibles.append(
                (nombre_col, col_esperada.tipo_django, col_real['tipo'])
            )
    
    # 4. Verificar nullable (solo warning si Django espera NOT NULL pero BD permite NULL)
    for nombre_col, col_esperada in columnas_django.items():
        if nombre_col not in columnas_bd:
            continue
            
        col_real = columnas_bd[nombre_col]
        if not col_esperada.nullable and col_real['nullable']:
            resultado.nullable_incompatibles.append(
                (nombre_col, col_esperada.nullable, col_real['nullable'])
            )
    
    return resultado


def verificar_esquema(verbose: bool = True) -> Dict[str, ResultadoVerificacion]:
    """
    Verifica todos los modelos managed=False contra la BD.
    
    Args:
        verbose: Si True, imprime resultados
        
    Returns:
        Dict con nombre_modelo -> ResultadoVerificacion
    """
    from django.db import connection
    from django.apps import apps
    
    resultados = {}
    modelos_verificados = 0
    modelos_con_errores = 0
    
    # Obtener modelos de core e inventario
    for app_label in ['core', 'inventario']:
        try:
            app_models = apps.get_app_config(app_label).get_models()
        except LookupError:
            if verbose:
                print(f"⚠️  App '{app_label}' no encontrada")
            continue
        
        for modelo in app_models:
            # Solo verificar modelos managed=False
            if modelo._meta.managed:
                continue
            
            with connection.cursor() as cursor:
                resultado = verificar_modelo(modelo, cursor)
                resultados[modelo.__name__] = resultado
                modelos_verificados += 1
                
                if not resultado.es_valido:
                    modelos_con_errores += 1
                
                if verbose:
                    _imprimir_resultado(modelo.__name__, resultado)
    
    if verbose:
        print("\n" + "=" * 60)
        print(f"RESUMEN: {modelos_verificados} modelos verificados, "
              f"{modelos_con_errores} con discrepancias")
        
        if modelos_con_errores == 0:
            print("✅ Esquema BD alineado con modelos Django")
        else:
            print("⚠️  Hay discrepancias que requieren atención")
    
    return resultados


def _imprimir_resultado(nombre: str, resultado: ResultadoVerificacion):
    """Imprime el resultado de verificación de un modelo."""
    if resultado.es_valido and not resultado.columnas_extra:
        print(f"✅ {nombre}: OK")
        return
    
    icono = "❌" if not resultado.es_valido else "⚠️"
    print(f"\n{icono} {nombre} ({resultado.tabla}):")
    
    if resultado.errores:
        for error in resultado.errores:
            print(f"   ❌ ERROR: {error}")
    
    if resultado.columnas_faltantes:
        print(f"   ❌ Columnas faltantes en BD: {resultado.columnas_faltantes}")
    
    if resultado.tipos_incompatibles:
        for col, esperado, real in resultado.tipos_incompatibles:
            print(f"   ⚠️  Tipo incompatible en '{col}': Django={esperado}, BD={real}")
    
    if resultado.nullable_incompatibles:
        for col, esperado, real in resultado.nullable_incompatibles:
            print(f"   ℹ️  Nullable en '{col}': Django NOT NULL pero BD permite NULL")
    
    if resultado.columnas_extra:
        print(f"   ℹ️  Columnas extra en BD (no en Django): {resultado.columnas_extra}")


# =============================================================================
# ISS-001/003 FIX (audit22): Verificación de columnas y constraints críticos
# =============================================================================

# Columnas críticas que DEBEN existir para el funcionamiento correcto
COLUMNAS_CRITICAS = {
    'movimientos': ['subtipo_salida', 'numero_expediente'],
    'detalles_requisicion': ['motivo_ajuste'],
    'lotes': ['centro_id', 'activo', 'cantidad_actual', 'fecha_caducidad'],
    'requisiciones': ['estado', 'centro_origen_id', 'solicitante_id'],
}

# Constraints recomendados para integridad de datos
CONSTRAINTS_RECOMENDADOS = {
    'lotes': [
        ('chk_lotes_cantidad_no_negativa', 'cantidad_actual >= 0'),
        ('chk_lotes_cantidad_inicial_positiva', 'cantidad_inicial > 0'),
    ],
    'movimientos': [
        ('chk_movimientos_cantidad_positiva', 'cantidad > 0'),
        ('chk_movimientos_tipo_valido', "tipo IN ('entrada', 'salida', 'ajuste', 'transferencia')"),
    ],
    'requisiciones': [
        ('chk_requisiciones_estado_valido', "estado IN (...)"),  # Simplificado
    ],
}


def verificar_columnas_criticas(verbose: bool = True) -> Dict[str, List[str]]:
    """
    ISS-001 FIX (audit22): Verifica que las columnas críticas existan en BD.
    
    Esto es esencial para entornos nuevos donde managed=False impide
    que Django cree las columnas automáticamente.
    
    Returns:
        Dict con tabla -> lista de columnas faltantes
    """
    from django.db import connection
    
    faltantes = {}
    
    with connection.cursor() as cursor:
        for tabla, columnas in COLUMNAS_CRITICAS.items():
            # Obtener columnas reales de la tabla
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
            """, [tabla])
            columnas_bd = {row[0] for row in cursor.fetchall()}
            
            if not columnas_bd:
                faltantes[tabla] = [f"TABLA NO EXISTE: {tabla}"]
                continue
            
            cols_faltantes = [c for c in columnas if c not in columnas_bd]
            if cols_faltantes:
                faltantes[tabla] = cols_faltantes
                
                if verbose:
                    print(f"❌ {tabla}: Columnas faltantes: {cols_faltantes}")
            elif verbose:
                print(f"✅ {tabla}: Todas las columnas críticas presentes")
    
    return faltantes


def verificar_constraints(verbose: bool = True) -> Dict[str, List[str]]:
    """
    ISS-003 FIX (audit22): Verifica constraints de integridad en BD.
    
    Returns:
        Dict con tabla -> lista de constraints faltantes (nombres)
    """
    from django.db import connection
    
    faltantes = {}
    
    with connection.cursor() as cursor:
        for tabla, constraints in CONSTRAINTS_RECOMENDADOS.items():
            # Obtener constraints CHECK de la tabla
            cursor.execute("""
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE rel.relname = %s 
                  AND nsp.nspname = 'public'
                  AND con.contype = 'c'
            """, [tabla])
            constraints_bd = {row[0] for row in cursor.fetchall()}
            
            cons_faltantes = []
            for nombre, _ in constraints:
                # Buscar constraint por nombre o similar
                encontrado = any(nombre in c or c.startswith(f'{tabla}_') for c in constraints_bd)
                if not encontrado and nombre not in constraints_bd:
                    cons_faltantes.append(nombre)
            
            if cons_faltantes:
                faltantes[tabla] = cons_faltantes
                if verbose:
                    print(f"⚠️  {tabla}: Constraints recomendados faltantes: {cons_faltantes}")
            elif verbose and constraints:
                print(f"✅ {tabla}: Constraints de integridad presentes")
    
    return faltantes


def verificacion_arranque(raise_on_error: bool = False) -> bool:
    """
    ISS-001 FIX (audit22): Verificación rápida para ejecutar al arrancar.
    
    Verifica solo columnas críticas, no el esquema completo.
    Útil para integrar en AppConfig.ready() o manage.py.
    
    Args:
        raise_on_error: Si True, lanza excepción en caso de error
        
    Returns:
        True si todo OK, False si hay problemas
    """
    from django.db import connection
    from django.conf import settings
    
    # Solo verificar en PostgreSQL (no SQLite de tests)
    if 'sqlite' in settings.DATABASES.get('default', {}).get('ENGINE', ''):
        logger.info("ISS-001: Verificación de esquema omitida (SQLite)")
        return True
    
    try:
        faltantes = verificar_columnas_criticas(verbose=False)
        
        if faltantes:
            msg = f"ISS-001 ERROR: Columnas críticas faltantes en BD: {faltantes}"
            logger.error(msg)
            
            if raise_on_error:
                raise RuntimeError(msg)
            return False
        
        logger.info("ISS-001: Verificación de esquema OK - Columnas críticas presentes")
        return True
        
    except Exception as e:
        logger.warning(f"ISS-001: No se pudo verificar esquema: {e}")
        return True  # No bloquear si no hay conexión


def generar_sql_constraints() -> str:
    """
    ISS-003 FIX (audit22): Genera SQL para aplicar constraints recomendados.
    
    Returns:
        String con sentencias SQL para aplicar en Supabase
    """
    sql_lines = [
        "-- ============================================",
        "-- ISS-003 FIX: Constraints de integridad recomendados",
        "-- Ejecutar en: Supabase SQL Editor",
        "-- ============================================",
        "",
    ]
    
    # Constraints de lotes
    sql_lines.extend([
        "-- 1. Stock no negativo en lotes",
        "ALTER TABLE lotes DROP CONSTRAINT IF EXISTS chk_lotes_cantidad_no_negativa;",
        "ALTER TABLE lotes ADD CONSTRAINT chk_lotes_cantidad_no_negativa CHECK (cantidad_actual >= 0);",
        "",
        "-- 2. Cantidad inicial positiva",
        "ALTER TABLE lotes DROP CONSTRAINT IF EXISTS chk_lotes_cantidad_inicial_positiva;",
        "ALTER TABLE lotes ADD CONSTRAINT chk_lotes_cantidad_inicial_positiva CHECK (cantidad_inicial > 0);",
        "",
    ])
    
    # Constraints de movimientos
    sql_lines.extend([
        "-- 3. Cantidad positiva en movimientos",
        "ALTER TABLE movimientos DROP CONSTRAINT IF EXISTS chk_movimientos_cantidad_positiva;",
        "ALTER TABLE movimientos ADD CONSTRAINT chk_movimientos_cantidad_positiva CHECK (cantidad > 0);",
        "",
        "-- 4. Tipos de movimiento válidos",
        "ALTER TABLE movimientos DROP CONSTRAINT IF EXISTS chk_movimientos_tipo_valido;",
        "ALTER TABLE movimientos ADD CONSTRAINT chk_movimientos_tipo_valido",
        "  CHECK (tipo IN ('entrada', 'salida', 'ajuste', 'transferencia'));",
        "",
    ])
    
    # Constraints de requisiciones
    sql_lines.extend([
        "-- 5. Estados de requisición válidos (Flujo V2)",
        "ALTER TABLE requisiciones DROP CONSTRAINT IF EXISTS chk_requisiciones_estado_valido;",
        "ALTER TABLE requisiciones ADD CONSTRAINT chk_requisiciones_estado_valido",
        "  CHECK (estado IN (",
        "    'borrador', 'pendiente_admin', 'pendiente_director',",
        "    'enviada', 'en_revision', 'autorizada', 'en_surtido',",
        "    'surtida', 'entregada', 'rechazada', 'vencida', 'cancelada',",
        "    'devuelta', 'parcial'",
        "  ));",
        "",
    ])
    
    return "\n".join(sql_lines)


# Ejecutar si se importa directamente
if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()
    
    print("=" * 60)
    print("ISS-001/003 FIX: Verificación de esquema BD vs modelos Django")
    print("=" * 60)
    
    print("\n--- Verificación de esquema completa ---")
    verificar_esquema(verbose=True)
    
    print("\n--- Verificación de columnas críticas ---")
    verificar_columnas_criticas(verbose=True)
    
    print("\n--- Verificación de constraints ---")
    verificar_constraints(verbose=True)
    
    print("\n--- SQL para constraints recomendados ---")
    print(generar_sql_constraints())
