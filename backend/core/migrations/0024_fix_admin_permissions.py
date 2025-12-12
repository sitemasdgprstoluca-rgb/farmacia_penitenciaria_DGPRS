# audit35: Fix user permissions in Supabase
# ISS-DEPLOY: Ensure all users have correct rol field based on their attributes

from django.db import migrations


def fix_all_user_permissions(apps, schema_editor):
    """
    Fix ALL user permissions directly in the database.
    The usuarios table is unmanaged, so we use raw SQL.
    
    Logic:
    1. is_superuser=TRUE -> rol='admin_sistema'
    2. is_staff=TRUE (no superuser) -> rol='farmacia'
    3. has centro_id -> rol='centro'
    4. others -> rol='vista'
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # 1. Fix superusers -> admin_sistema
        cursor.execute("""
            UPDATE usuarios 
            SET rol = 'admin_sistema',
                is_active = TRUE,
                activo = TRUE
            WHERE is_superuser = TRUE
        """)
        superuser_count = cursor.rowcount
        print(f"Updated {superuser_count} superusers to admin_sistema")
        
        # 2. Fix staff (non-superuser) -> farmacia
        cursor.execute("""
            UPDATE usuarios 
            SET rol = 'farmacia',
                is_active = TRUE,
                activo = TRUE
            WHERE is_staff = TRUE 
              AND (is_superuser = FALSE OR is_superuser IS NULL)
              AND (rol IS NULL OR rol = '' OR rol NOT IN ('admin_sistema', 'farmacia'))
        """)
        staff_count = cursor.rowcount
        print(f"Updated {staff_count} staff users to farmacia")
        
        # 3. Fix users with centro -> centro
        cursor.execute("""
            UPDATE usuarios 
            SET rol = 'centro',
                is_active = TRUE,
                activo = TRUE
            WHERE centro_id IS NOT NULL
              AND (is_superuser = FALSE OR is_superuser IS NULL)
              AND (is_staff = FALSE OR is_staff IS NULL)
              AND (rol IS NULL OR rol = '' OR rol NOT IN ('admin_sistema', 'farmacia', 'centro'))
        """)
        centro_count = cursor.rowcount
        print(f"Updated {centro_count} centro users")
        
        # 4. Fix remaining users -> vista
        cursor.execute("""
            UPDATE usuarios 
            SET rol = 'vista',
                is_active = TRUE,
                activo = TRUE
            WHERE (rol IS NULL OR rol = '')
              AND (is_superuser = FALSE OR is_superuser IS NULL)
              AND (is_staff = FALSE OR is_staff IS NULL)
        """)
        vista_count = cursor.rowcount
        print(f"Updated {vista_count} users to vista")
        
        # 5. Ensure admin user exists and has correct permissions
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE username = 'admin'")
        if cursor.fetchone()[0] > 0:
            cursor.execute("""
                UPDATE usuarios 
                SET is_superuser = TRUE,
                    is_staff = TRUE,
                    is_active = TRUE,
                    activo = TRUE,
                    rol = 'admin_sistema'
                WHERE username = 'admin'
            """)
            print("Admin user permissions enforced")
        
        # Log current state
        cursor.execute("""
            SELECT username, is_superuser, is_staff, is_active, rol, centro_id
            FROM usuarios 
            ORDER BY username
            LIMIT 20
        """)
        print("\nFirst 20 users after fix:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: superuser={row[1]}, staff={row[2]}, active={row[3]}, rol={row[4]}, centro={row[5]}")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_add_activo_column'),
    ]

    operations = [
        migrations.RunPython(fix_all_user_permissions, noop),
    ]
