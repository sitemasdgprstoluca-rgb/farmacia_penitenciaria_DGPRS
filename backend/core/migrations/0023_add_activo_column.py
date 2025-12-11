# audit35: Add missing activo column to usuarios
# ISS-DEPLOY: Migration 0022 was already applied without activo column
# This migration adds it idempotently

from django.db import migrations


def add_activo_column(apps, schema_editor):
    """
    Add activo column if it doesn't exist.
    Uses IF NOT EXISTS for idempotency.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'usuarios' AND column_name = 'activo'
        """)
        
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE usuarios 
                ADD COLUMN activo BOOLEAN DEFAULT TRUE
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
