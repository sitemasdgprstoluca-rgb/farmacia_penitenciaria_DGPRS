# audit35: Fix admin user permissions in Supabase
# ISS-DEPLOY: Ensure admin user has correct is_superuser and rol

from django.db import migrations


def fix_admin_permissions(apps, schema_editor):
    """
    Fix admin user permissions directly in the database.
    The usuarios table is unmanaged, so we use raw SQL.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Ensure admin has is_superuser=True and correct rol
        cursor.execute("""
            UPDATE usuarios 
            SET is_superuser = TRUE,
                is_staff = TRUE,
                is_active = TRUE,
                rol = 'admin_sistema'
            WHERE username = 'admin'
        """)
        
        # Also ensure farmacia user has correct rol
        cursor.execute("""
            UPDATE usuarios 
            SET is_staff = TRUE,
                is_active = TRUE,
                rol = 'farmacia'
            WHERE username = 'farmacia'
        """)
        
        print("Admin and farmacia user permissions fixed.")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_add_activo_column'),
    ]

    operations = [
        migrations.RunPython(fix_admin_permissions, noop),
    ]
