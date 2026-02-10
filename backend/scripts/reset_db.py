import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.core.management import call_command
import shutil

print("=" * 60)
print("🔄 RESETEAR BASE DE DATOS")
print("=" * 60)

# 1. Eliminar base de datos SQLite
db_path = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
if os.path.exists(db_path):
    os.remove(db_path)
    print("✅ Base de datos eliminada")

# 2. Eliminar migraciones antiguas
migrations_paths = [
    os.path.join(os.path.dirname(__file__), 'inventario', 'migrations'),
    os.path.join(os.path.dirname(__file__), 'core', 'migrations'),
]

for migrations_path in migrations_paths:
    if os.path.exists(migrations_path):
        for file in os.listdir(migrations_path):
            if file.startswith('0') and file.endswith('.py'):
                file_path = os.path.join(migrations_path, file)
                os.remove(file_path)
                print(f"✅ Migración eliminada: {file}")

print("\n📝 Creando nuevas migraciones...")

# 3. Crear migraciones frescas
try:
    call_command('makemigrations', 'inventario')
    print("✅ Migraciones de inventario creadas")
except:
    pass

try:
    call_command('makemigrations', 'core')
    print("✅ Migraciones de core creadas")
except:
    pass

# 4. Aplicar migraciones
print("\n🔧 Aplicando migraciones...")
call_command('migrate')
print("✅ Migraciones aplicadas")

print("\n" + "=" * 60)
print("✅ BASE DE DATOS RESETEADA EXITOSAMENTE")
print("=" * 60)
print("\n📌 SIGUIENTE PASO:")
print("   1. python manage.py createsuperuser")
print("   2. python poblar_db.py")
print("   3. python manage.py runserver 8000")
print("=" * 60)
