"""
Script para verificar la ubicación de los lotes y centros configurados
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Centro, Lote
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
import json

User = get_user_model()

print("="*80)
print("VERIFICACIÓN DE UBICACIÓN DE LOTES")
print("="*80)

# 1. Centros existentes
print("\n1. CENTROS EXISTENTES:")
print("-" * 40)
centros = Centro.objects.all()
for centro in centros:
    lotes_count = Lote.objects.filter(centro=centro, activo=True).count()
    stock_total = Lote.objects.filter(centro=centro, activo=True).aggregate(
        total=Sum('cantidad_actual')
    )['total'] or 0
    print(f"  - {centro.nombre} (ID: {centro.id})")
    print(f"    Lotes activos: {lotes_count}")
    print(f"    Stock total: {stock_total}")

# 2. Lotes SIN centro (farmacia central)
print("\n2. LOTES SIN CENTRO (FARMACIA CENTRAL):")
print("-" * 40)
lotes_sin_centro = Lote.objects.filter(centro__isnull=True, activo=True)
print(f"  Total lotes: {lotes_sin_centro.count()}")
stock_sin_centro = lotes_sin_centro.aggregate(total=Sum('cantidad_actual'))['total'] or 0
print(f"  Stock total: {stock_sin_centro}")

if lotes_sin_centro.exists():
    print("\n  Primeros 10 lotes:")
    for lote in lotes_sin_centro[:10]:
        print(f"    - {lote.producto.clave}: {lote.numero_lote} = {lote.cantidad_actual} unidades")

# 3. Usuarios de farmacia
print("\n3. USUARIOS DE FARMACIA:")
print("-" * 40)
try:
    usuarios_farmacia = User.objects.filter(
        rol__in=['farmacia', 'admin_farmacia', 'farmaceutico', 'usuario_farmacia']
    )
    for user in usuarios_farmacia:
        centro_nombre = user.centro.nombre if user.centro else "Sin centro (Farmacia Central)"
        print(f"  - {user.username} (rol: {user.rol})")
        print(f"    Centro: {centro_nombre}")
except Exception as e:
    print(f"  ⚠️ No se pudieron cargar usuarios: {e}")

# 4. Resumen
print("\n4. RESUMEN:")
print("-" * 40)
total_lotes = Lote.objects.filter(activo=True).count()
lotes_con_centro = Lote.objects.filter(centro__isnull=False, activo=True).count()
lotes_sin_centro_count = Lote.objects.filter(centro__isnull=True, activo=True).count()

print(f"  Total lotes activos: {total_lotes}")
print(f"  Lotes asignados a centros: {lotes_con_centro}")
print(f"  Lotes en farmacia central (sin centro): {lotes_sin_centro_count}")

# 5. DIAGNÓSTICO DEL PROBLEMA
print("\n5. DIAGNÓSTICO:")
print("=" * 80)
if lotes_sin_centro_count == 0 and lotes_con_centro > 0:
    print("⚠️ PROBLEMA DETECTADO:")
    print("  - NO hay lotes en farmacia central (centro__isnull=True)")
    print("  - Todos los lotes están asignados a centros específicos")
    print("\n  SOLUCIÓN:")
    print("  - Opción 1: Mover lotes al centro 'Farmacia' configurándolos con centro=NULL")
    print("  - Opción 2: Si existe un centro llamado 'Farmacia', modificar la lógica")
    print("              para considerar ese centro como farmacia central")
    
    # Buscar si existe centro 'Farmacia'
    centro_farmacia = Centro.objects.filter(nombre__icontains='farmacia').first()
    if centro_farmacia:
        lotes_en_farmacia = Lote.objects.filter(centro=centro_farmacia, activo=True).count()
        print(f"\n  ✓ Encontrado centro: {centro_farmacia.nombre} (ID: {centro_farmacia.id})")
        print(f"    Tiene {lotes_en_farmacia} lotes activos")
        print(f"\n  RECOMENDACIÓN: Modificar el código para que cuando se busque")
        print(f"  'farmacia central', también incluya el centro ID={centro_farmacia.id}")
else:
    print("✓ Configuración correcta:")
    print(f"  - Hay {lotes_sin_centro_count} lotes en farmacia central")
