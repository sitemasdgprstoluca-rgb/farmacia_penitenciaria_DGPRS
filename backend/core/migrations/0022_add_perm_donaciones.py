# audit34: Add missing permission fields to Usuario
# ISS-DEPLOY: Idempotent migration - uses IF NOT EXISTS for production safety
# These fields may already exist in Supabase but need to be in Django migrations

from django.db import migrations


def add_column_if_not_exists(apps, schema_editor):
    """
    Add permission columns only if they don't already exist.
    This makes the migration idempotent for production where columns
    may have been added directly to Supabase.
    
    HALLAZGO #7: Compatible con PostgreSQL y SQLite
    Usa introspección de Django en lugar de information_schema
    """
    from django.db import connection
    
    # Obtener columnas existentes usando introspección de Django (compatible con todos los motores)
    with connection.cursor() as cursor:
        # Obtener descripción de la tabla usuarios
        table_name = 'usuarios'
        
        # Verificar si la tabla existe
        if connection.vendor == 'postgresql':
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s
            """, [table_name])
        elif connection.vendor == 'sqlite':
            cursor.execute(f"PRAGMA table_info({table_name})")
        else:
            # MySQL/MariaDB
            cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        
        # Extraer nombres de columnas según el motor
        if connection.vendor == 'postgresql':
            existing_columns = {row[0] for row in cursor.fetchall()}
        elif connection.vendor == 'sqlite':
            # PRAGMA table_info retorna: (cid, name, type, notnull, dflt_value, pk)
            existing_columns = {row[1] for row in cursor.fetchall()}
        else:
            # MySQL: SHOW COLUMNS retorna: (Field, Type, Null, Key, Default, Extra)
            existing_columns = {row[0] for row in cursor.fetchall()}
        
        # Definir columnas a agregar con tipos específicos por motor
        columns_to_add = [
            'perm_donaciones',
            'perm_crear_requisicion',
            'perm_autorizar_admin',
            'perm_autorizar_director',
            'perm_recibir_farmacia',
            'perm_autorizar_farmacia',
            'perm_surtir',
            'perm_confirmar_entrega',
            'activo',
        ]
        
        # Agregar columnas faltantes
        for col_name in columns_to_add:
            if col_name not in existing_columns:
                if connection.vendor == 'postgresql':
                    # PostgreSQL soporta IF NOT EXISTS
                    col_type = 'BOOLEAN DEFAULT TRUE' if col_name == 'activo' else 'BOOLEAN'
                    cursor.execute(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN IF NOT EXISTS {col_name} {col_type} NULL
                    """)
                elif connection.vendor == 'sqlite':
                    # SQLite no soporta IF NOT EXISTS en ALTER TABLE, pero no falla si ya existe
                    col_type = 'INTEGER DEFAULT 1' if col_name == 'activo' else 'INTEGER'
                    try:
                        cursor.execute(f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN {col_name} {col_type}
                        """)
                    except Exception:
                        # Columna ya existe, ignorar
                        pass
                else:
                    # MySQL/MariaDB
                    col_type = 'TINYINT(1) DEFAULT 1' if col_name == 'activo' else 'TINYINT(1)'
                    cursor.execute(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN IF NOT EXISTS {col_name} {col_type} NULL
                    """)


def noop(apps, schema_editor):
    """Reverse migration is a no-op since we can't know if columns existed before."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_optimize_db_structure'),
    ]

    operations = [
        migrations.RunPython(add_column_if_not_exists, noop),
    ]
