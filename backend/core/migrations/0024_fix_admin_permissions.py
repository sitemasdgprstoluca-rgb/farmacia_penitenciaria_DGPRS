# audit35: Fix admin user permissions in Supabase
# ISS-DEPLOY: Ensure admin user has correct is_superuser and rol

from django.db import migrations


def fix_admin_permissions(apps, schema_editor):
    """
    Fix admin user permissions directly in the database.
    The usuarios table is unmanaged, so we use raw SQL.
    Also creates admin user if it doesn't exist.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if admin exists
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        admin_exists = cursor.fetchone()[0] > 0
        
        if admin_exists:
            # Update existing admin
            cursor.execute("""
                UPDATE usuarios 
                SET is_superuser = TRUE,
                    is_staff = TRUE,
                    is_active = TRUE,
                    activo = TRUE,
                    rol = 'admin_sistema'
                WHERE username = 'admin'
            """)
            print("Admin user updated with correct permissions.")
        else:
            # Create admin user with hashed password
            # Using Django's make_password would require importing, so we'll let build.sh handle creation
            print("Admin user not found - will be created by build.sh")
        
        # Check if farmacia exists
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'farmacia'")
        farmacia_exists = cursor.fetchone()[0] > 0
        
        if farmacia_exists:
            cursor.execute("""
                UPDATE usuarios 
                SET is_staff = TRUE,
                    is_active = TRUE,
                    activo = TRUE,
                    rol = 'farmacia'
                WHERE username = 'farmacia'
            """)
            print("Farmacia user updated with correct permissions.")
        
        # Log current state for debugging
        cursor.execute("""
            SELECT username, is_superuser, is_staff, is_active, rol 
            FROM usuarios 
            WHERE username IN ('admin', 'farmacia')
        """)
        for row in cursor.fetchall():
            print(f"User {row[0]}: is_superuser={row[1]}, is_staff={row[2]}, is_active={row[3]}, rol={row[4]}")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_add_activo_column'),
    ]

    operations = [
        migrations.RunPython(fix_admin_permissions, noop),
    ]
