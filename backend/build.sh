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
# 1. Obtener centros existentes de la BD
# ============================================
print("Centros existentes en BD:")
centros_existentes = {c.clave: c for c in Centro.objects.all()}
for clave, centro in centros_existentes.items():
    print(f"  - {clave}: {centro.nombre}")

# Obtener el primer centro tipo CERESO para asignar a usuarios de prueba
centros_cereso = Centro.objects.filter(tipo='cereso', activo=True).order_by('clave')[:2]
centro1 = centros_cereso[0] if len(centros_cereso) > 0 else None
centro2 = centros_cereso[1] if len(centros_cereso) > 1 else None

print(f"\nCentros para usuarios de prueba:")
print(f"  centro1 -> {centro1.nombre if centro1 else 'N/A'}")
print(f"  centro2 -> {centro2.nombre if centro2 else 'N/A'}")

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
        'centro': None,
    },
    # Usuario de Centro 1
    {
        'username': 'centro1',
        'email': 'centro1@cereso.gob.mx',
        'password': 'Centro123!',
        'is_staff': False,
        'is_superuser': False,
        'is_active': True,
        'rol': 'centro',
        'first_name': 'Usuario',
        'last_name': centro1.nombre if centro1 else 'Centro 1',
        'centro': centro1,
    },
    # Usuario de Centro 2
    {
        'username': 'centro2',
        'email': 'centro2@cereso.gob.mx',
        'password': 'Centro123!',
        'is_staff': False,
        'is_superuser': False,
        'is_active': True,
        'rol': 'centro',
        'first_name': 'Usuario',
        'last_name': centro2.nombre if centro2 else 'Centro 2',
        'centro': centro2,
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

print("\nCreando/actualizando usuarios:")
for u_data in usuarios_data:
    password = u_data.pop('password')
    centro_obj = u_data.pop('centro')
    
    # Solo crear usuarios de centro si hay centros disponibles
    if u_data['rol'] == 'centro' and centro_obj is None:
        print(f"  SKIP: {u_data['username']} (no hay centro disponible)")
        continue
    
    user, created = User.objects.update_or_create(
        username=u_data['username'],
        defaults={**u_data, 'centro': centro_obj}
    )
    user.set_password(password)
    user.save()
    centro_info = f" -> {centro_obj.nombre}" if centro_obj else ""
    print(f"  {'NUEVO' if created else 'ACTUALIZADO'}: {user.username} (rol: {user.rol}){centro_info}")

print(f"\n=== Total: {User.objects.count()} usuarios, {Centro.objects.count()} centros ===")
print("\n" + "="*50)
print("CREDENCIALES DE ACCESO:")
print("="*50)
print("  admin     / Admin123!     - Superusuario")
print("  farmacia  / Farmacia123!  - Gestión inventario")
print("  centro1   / Centro123!    - Usuario centro")
print("  centro2   / Centro123!    - Usuario centro")
print("  vista     / Vista123!     - Solo lectura")
print("="*50)
print("\n📋 CREDENCIALES DE PRUEBA:")
print("  admin     / Admin123!     (o ADMIN_PASSWORD) - Superusuario")
print("  farmacia  / Farmacia123!  - Gestión de inventario")
print("  centro1   / Centro123!    - CERESO Almoloya")
print("  centro2   / Centro123!    - CERESO Ecatepec")
print("  vista     / Vista123!     - Solo lectura")
EOF

echo "=== Build complete ==="
