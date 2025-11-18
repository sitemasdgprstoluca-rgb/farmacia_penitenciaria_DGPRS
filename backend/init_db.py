import os
import sys
import django
from pathlib import Path

# Configurar Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

print("=" * 60)
print("🔧 INICIALIZANDO BASE DE DATOS")
print("=" * 60)

# Verificar si existe db.sqlite3
db_path = BASE_DIR / 'db.sqlite3'
db_exists = db_path.exists()

if db_exists:
    print(f"✅ Base de datos encontrada: {db_path}")
else:
    print(f"⚠️  Base de datos NO encontrada, se creará: {db_path}")

# Setup Django
django.setup()

from django.core.management import call_command
from django.db import connection

# Verificar si las tablas existen
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
    if len(tables) > 0:
        print(f"\n✅ Base de datos con {len(tables)} tablas encontradas")
        print("   No es necesario crear migraciones")
    else:
        print("\n⚠️  Base de datos vacía, creando estructura...")
        crear_estructura()
        
except Exception as e:
    print(f"\n⚠️  Error al verificar BD: {e}")
    print("   Creando estructura desde cero...")
    crear_estructura()

def crear_estructura():
    """Crea las migraciones y estructura de BD"""
    print("\n📝 Paso 1: Creando migraciones...")
    
    try:
        call_command('makemigrations', 'core', verbosity=1)
        print("✅ Migraciones de 'core' creadas")
    except Exception as e:
        print(f"ℹ️  core: {e}")
    
    try:
        call_command('makemigrations', 'inventario', verbosity=1)
        print("✅ Migraciones de 'inventario' creadas")
    except Exception as e:
        print(f"ℹ️  inventario: {e}")
    
    print("\n🔧 Paso 2: Aplicando migraciones...")
    call_command('migrate', verbosity=1)
    print("✅ Migraciones aplicadas")
    
    print("\n👤 Paso 3: Verificando usuario admin...")
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("✅ Usuario admin creado (admin/admin123)")
    else:
        print("ℹ️  Usuario admin ya existe")

print("\n" + "=" * 60)
print("✅ INICIALIZACIÓN COMPLETADA")
print("=" * 60)
