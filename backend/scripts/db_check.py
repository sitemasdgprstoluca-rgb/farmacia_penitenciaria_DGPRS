import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection
from inventario.models import Producto, Lote, Centro, Movimiento, Requisicion

print("=" * 60)
print("🔍 VERIFICACIÓN DE BASE DE DATOS Y MODELOS")
print("=" * 60)

# Test de conexión
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        print("✅ Conexión a base de datos: OK")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    sys.exit(1)

# Verificar tablas
print("\n📊 CONTEO DE REGISTROS:")
print("-" * 60)

try:
    productos_count = Producto.objects.count()
    print(f"  Productos: {productos_count}")
except Exception as e:
    print(f"  ❌ Productos: Error - {e}")

try:
    lotes_count = Lote.objects.count()
    print(f"  Lotes: {lotes_count}")
except Exception as e:
    print(f"  ❌ Lotes: Error - {e}")

try:
    centros_count = Centro.objects.count()
    print(f"  Centros: {centros_count}")
except Exception as e:
    print(f"  ❌ Centros: Error - {e}")

try:
    movimientos_count = Movimiento.objects.count()
    print(f"  Movimientos: {movimientos_count}")
except Exception as e:
    print(f"  ❌ Movimientos: Error - {e}")

try:
    requisiciones_count = Requisicion.objects.count()
    print(f"  Requisiciones: {requisiciones_count}")
except Exception as e:
    print(f"  ❌ Requisiciones: Error - {e}")

print("\n" + "=" * 60)
print("✅ VERIFICACIÓN COMPLETADA")
print("=" * 60)
