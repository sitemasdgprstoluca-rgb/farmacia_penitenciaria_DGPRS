import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

print("=" * 60)
print("🔍 DIAGNÓSTICO RÁPIDO")
print("=" * 60)

# Test 1: Imports
try:
    from inventario.models import Producto, Lote, Centro
    from django.contrib.auth.models import Group
    from django.contrib.auth import get_user_model
    User = get_user_model()
    print("✅ Imports: OK")
except Exception as e:
    print(f"❌ Imports: {e}")

# Test 2: Base de datos
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("✅ Database: OK")
except Exception as e:
    print(f"❌ Database: {e}")

# Test 3: Modelos
try:
    print(f"  Productos: {Producto.objects.count()}")
    print(f"  Lotes: {Lote.objects.count()}")
    print(f"  Centros: {Centro.objects.count()}")
    print(f"  Usuarios: {User.objects.count()}")
    print("✅ Models: OK")
except Exception as e:
    print(f"❌ Models: {e}")

print("=" * 60)
