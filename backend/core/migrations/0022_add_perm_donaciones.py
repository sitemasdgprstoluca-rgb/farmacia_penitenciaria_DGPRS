# audit34: Add missing permission fields to Usuario
# ISS-DEPLOY: Idempotent migration - uses IF NOT EXISTS for production safety
# These fields may already exist in Supabase but need to be in Django migrations

from django.db import migrations


def add_column_if_not_exists(apps, schema_editor):
    """
    Add permission columns only if they don't already exist.
    This makes the migration idempotent for production where columns
    may have been added directly to Supabase.
    """
    from django.db import connection
    
    columns_to_add = [
        ('perm_donaciones', 'BOOLEAN'),
        ('perm_crear_requisicion', 'BOOLEAN'),
        ('perm_autorizar_admin', 'BOOLEAN'),
        ('perm_autorizar_director', 'BOOLEAN'),
        ('perm_recibir_farmacia', 'BOOLEAN'),
        ('perm_autorizar_farmacia', 'BOOLEAN'),
        ('perm_surtir', 'BOOLEAN'),
        ('perm_confirmar_entrega', 'BOOLEAN'),
    ]
    
    with connection.cursor() as cursor:
        # Check existing columns
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'usuarios'
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        
        # Add missing columns
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                cursor.execute(f"""
                    ALTER TABLE usuarios 
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
