# audit35: Add missing activo column to usuarios
# ISS-DEPLOY: Migration 0022 was already applied without activo column
# This migration adds it idempotently
# HALLAZGO #7: Compatible con PostgreSQL/SQLite/MySQL

from django.db import migrations


def add_activo_column(apps, schema_editor):
    """
    Add activo column if it doesn't exist.
    Compatible con PostgreSQL, SQLite y MySQL.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        table_name = 'usuarios'
        column_name = 'activo'
        
        # Verificar si la columna existe según el motor de BD
        if connection.vendor == 'postgresql':
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = %s
            """, [table_name, column_name])
        elif connection.vendor == 'sqlite':
            cursor.execute(f"PRAGMA table_info({table_name})")
        else:
            # MySQL/MariaDB
            cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", [column_name])
        
        # Verificar si existe
        if connection.vendor == 'sqlite':
            # PRAGMA retorna: (cid, name, type, notnull, dflt_value, pk)
            existing = any(row[1] == column_name for row in cursor.fetchall())
        else:
            existing = cursor.fetchone() is not None
        
        # Agregar columna si no existe
        if not existing:
            if connection.vendor == 'postgresql':
                cursor.execute("""
                    ALTER TABLE usuarios 
                    ADD COLUMN IF NOT EXISTS activo BOOLEAN DEFAULT TRUE
                """)
            elif connection.vendor == 'sqlite':
                # SQLite no soporta IF NOT EXISTS, pero ya verificamos arriba
                try:
                    cursor.execute("""
                        ALTER TABLE usuarios 
                        ADD COLUMN activo INTEGER DEFAULT 1
                    """)
                except Exception:
                    # Columna ya existe
                    pass
            else:
                # MySQL/MariaDB
                cursor.execute("""
                    ALTER TABLE usuarios 
                    ADD COLUMN IF NOT EXISTS activo TINYINT(1) DEFAULT 1
                """)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_add_perm_donaciones'),
    ]

    operations = [
        migrations.RunPython(add_activo_column, noop),
    ]
