import os
import sys
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

print("=" * 60)
print("🔧 ARREGLANDO DEPENDENCIAS CIRCULARES")
print("=" * 60)

# 1. Eliminar db.sqlite3
db_path = BASE_DIR / 'db.sqlite3'
if db_path.exists():
    os.remove(db_path)
    print("✅ Base de datos eliminada")

# 2. Eliminar migraciones de core e inventario
apps = ['core', 'inventario']
for app in apps:
    migrations_path = BASE_DIR / app / 'migrations'
    if migrations_path.exists():
        for file in os.listdir(migrations_path):
            if file.startswith('0') and file.endswith('.py'):
                file_path = migrations_path / file
                os.remove(file_path)
                print(f"✅ Eliminada: {app}/migrations/{file}")

print("\n📝 Creando nuevas migraciones...")

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.core.management import call_command

# 3. Crear migraciones en orden correcto
print("\nPaso 1: Migraciones de core...")
call_command('makemigrations', 'core', verbosity=1)

print("\nPaso 2: Migraciones de inventario...")
call_command('makemigrations', 'inventario', verbosity=1)

# 4. Aplicar migraciones
print("\nPaso 3: Aplicando migraciones...")
call_command('migrate', verbosity=1)

# 5. Crear superusuario
print("\nPaso 4: Creando usuario admin...")
from django.contrib.auth import get_user_model
User = get_user_model()

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ Usuario admin creado (admin/admin123)")
else:
    print("ℹ️  Usuario admin ya existe")

print("\n" + "=" * 60)
print("✅ MIGRACIONES ARREGLADAS")
print("=" * 60)
print("\nAhora ejecuta:")
print("  python manage.py runserver 8000")
print("=" * 60)
