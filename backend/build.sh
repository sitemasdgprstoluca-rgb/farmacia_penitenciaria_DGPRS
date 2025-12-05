#!/usr/bin/env bash
# Script de build para Render

set -o errexit  # Salir en caso de error

echo "=== Installing dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --no-input

echo "=== Running migrations ==="
python manage.py migrate --no-input

echo "=== Creating/updating users ==="
python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
from core.models import Centro
import os

User = get_user_model()
admin_password = os.environ.get('ADMIN_PASSWORD', 'Admin123!')

# ============================================
# 1. Crear Centros si no existen
# ============================================
centros_data = [
    {'clave': 'FARM001', 'nombre': 'Farmacia Central', 'tipo': 'farmacia', 'activo': True},
    {'clave': 'CERESO01', 'nombre': 'CERESO Almoloya', 'tipo': 'cereso', 'activo': True},
    {'clave': 'CERESO02', 'nombre': 'CERESO Ecatepec', 'tipo': 'cereso', 'activo': True},
    {'clave': 'CERESO03', 'nombre': 'CERESO Nezahualcóyotl', 'tipo': 'cereso', 'activo': True},
]

centros_creados = {}
for c_data in centros_data:
    centro, created = Centro.objects.update_or_create(
        clave=c_data['clave'],
        defaults=c_data
    )
    centros_creados[c_data['clave']] = centro
    print(f"Centro {'creado' if created else 'actualizado'}: {centro.nombre}")

# ============================================
# 2. Crear usuarios de prueba
# ============================================
usuarios_data = [
    # Admin del sistema (superusuario)
    {
        'username': 'admin',
        'email': 'admin@farmacia.gob.mx',
        'password': admin_password,
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
        'rol': 'admin_sistema',
        'first_name': 'Administrador',
        'last_name': 'Sistema',
        'centro': None,
    },
    # Farmacia (puede gestionar todo el inventario)
    {
        'username': 'farmacia',
        'email': 'farmacia@farmacia.gob.mx',
        'password': 'Farmacia123!',
        'is_staff': True,
        'is_superuser': False,
        'is_active': True,
        'rol': 'farmacia',
        'first_name': 'Usuario',
        'last_name': 'Farmacia Central',
        'centro': None,  # Farmacia no tiene centro asignado
    },
    # Usuario de Centro 1 (CERESO Almoloya)
    {
        'username': 'centro1',
        'email': 'centro1@cereso.gob.mx',
        'password': 'Centro123!',
        'is_staff': False,
        'is_superuser': False,
        'is_active': True,
        'rol': 'centro',
        'first_name': 'Usuario',
        'last_name': 'CERESO Almoloya',
        'centro': 'CERESO01',
    },
    # Usuario de Centro 2 (CERESO Ecatepec)
    {
        'username': 'centro2',
        'email': 'centro2@cereso.gob.mx',
        'password': 'Centro123!',
        'is_staff': False,
        'is_superuser': False,
        'is_active': True,
        'rol': 'centro',
        'first_name': 'Usuario',
        'last_name': 'CERESO Ecatepec',
        'centro': 'CERESO02',
    },
    # Usuario Vista (solo lectura)
    {
        'username': 'vista',
        'email': 'vista@farmacia.gob.mx',
        'password': 'Vista123!',
        'is_staff': False,
        'is_superuser': False,
        'is_active': True,
        'rol': 'vista',
        'first_name': 'Usuario',
        'last_name': 'Solo Lectura',
        'centro': None,
    },
]

for u_data in usuarios_data:
    centro_clave = u_data.pop('centro')
    password = u_data.pop('password')
    
    # Obtener centro si aplica
    centro_obj = centros_creados.get(centro_clave) if centro_clave else None
    
    user, created = User.objects.update_or_create(
        username=u_data['username'],
        defaults={**u_data, 'centro': centro_obj}
    )
    user.set_password(password)
    user.save()
    print(f"Usuario {'creado' if created else 'actualizado'}: {user.username} (rol: {user.rol})")

print(f"\n=== Total: {User.objects.count()} usuarios, {Centro.objects.count()} centros ===")
print("\n📋 CREDENCIALES DE PRUEBA:")
print("  admin     / Admin123!     (o ADMIN_PASSWORD) - Superusuario")
print("  farmacia  / Farmacia123!  - Gestión de inventario")
print("  centro1   / Centro123!    - CERESO Almoloya")
print("  centro2   / Centro123!    - CERESO Ecatepec")
print("  vista     / Vista123!     - Solo lectura")
EOF

echo "=== Build complete ==="
