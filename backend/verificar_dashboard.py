#!/usr/bin/env python
"""Verificar que el dashboard tenga datos y funcione correctamente."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Producto, Lote, Movimiento, Centro, Requisicion
from django.utils import timezone
from datetime import timedelta

print("=" * 80)
print("VERIFICACIÓN DEL DASHBOARD")
print("=" * 80)

# 1. Verificar Productos
productos_count = Producto.objects.filter(activo=True).count()
print(f"\n✓ Productos activos: {productos_count}")

if productos_count == 0:
    print("  ⚠ No hay productos. Creando productos de prueba...")
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin = User.objects.filter(is_superuser=True).first()
    
    if admin:
        # Crear productos de prueba
        productos_prueba = [
            {'clave': 'MED-001', 'descripcion': 'Paracetamol 500mg', 'unidad_medida': 'tableta'},
            {'clave': 'MED-002', 'descripcion': 'Ibuprofeno 400mg', 'unidad_medida': 'tableta'},
            {'clave': 'MED-003', 'descripcion': 'Amoxicilina 500mg', 'unidad_medida': 'capsula'},
        ]
        
        for p_data in productos_prueba:
            Producto.objects.get_or_create(
                clave=p_data['clave'],
                defaults={
                    'descripcion': p_data['descripcion'],
                    'unidad_medida': p_data['unidad_medida'],
                    'stock_minimo': 100,
                    'stock_maximo': 1000,
                    'activo': True,
                    'created_by': admin
                }
            )
        print(f"  ✓ Creados {len(productos_prueba)} productos de prueba")

# 2. Verificar Lotes
lotes_count = Lote.objects.filter(estado='disponible', deleted_at__isnull=True).count()
print(f"\n✓ Lotes disponibles: {lotes_count}")

if lotes_count == 0:
    print("  ⚠ No hay lotes. Creando lotes de prueba...")
    productos = Producto.objects.filter(activo=True)[:3]
    centro = Centro.objects.first()
    
    for i, producto in enumerate(productos):
        Lote.objects.get_or_create(
            numero_lote=f'LOTE-2025-{i+1:03d}',
            defaults={
                'producto': producto,
                'centro': centro,
                'cantidad_inicial': 500,
                'cantidad_actual': 400,
                'fecha_caducidad': timezone.now().date() + timedelta(days=365),
                'estado': 'disponible'
            }
        )
    print(f"  ✓ Creados lotes de prueba")

# 3. Verificar Movimientos
movimientos_count = Movimiento.objects.count()
print(f"\n✓ Movimientos registrados: {movimientos_count}")

if movimientos_count < 10:
    print("  ⚠ Pocos movimientos. Creando movimientos de prueba...")
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin = User.objects.filter(is_superuser=True).first()
    lotes = Lote.objects.filter(estado='disponible')[:3]
    
    for i, lote in enumerate(lotes):
        # Entrada
        Movimiento.objects.create(
            tipo='entrada',
            lote=lote,
            cantidad=100,
            usuario=admin,
            observaciones=f'Entrada de prueba #{i+1}'
        )
        # Salida
        Movimiento.objects.create(
            tipo='salida',
            lote=lote,
            cantidad=-50,
            usuario=admin,
            observaciones=f'Salida de prueba #{i+1}'
        )
    print(f"  ✓ Creados movimientos de prueba")

# 4. Verificar Stock Total
from django.db.models import Sum
from django.db.models.functions import Coalesce
stock_total = Lote.objects.filter(
    estado='disponible',
    deleted_at__isnull=True
).aggregate(total=Coalesce(Sum('cantidad_actual'), 0))['total']

print(f"\n✓ Stock total en sistema: {stock_total} unidades")

# 5. Verificar Movimientos del Mes
inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
movimientos_mes = Movimiento.objects.filter(fecha__gte=inicio_mes).count()
print(f"✓ Movimientos este mes: {movimientos_mes}")

# 6. Verificar Requisiciones
requisiciones_count = Requisicion.objects.count()
print(f"✓ Requisiciones totales: {requisiciones_count}")

print("\n" + "=" * 80)
print("RESUMEN DEL DASHBOARD")
print("=" * 80)
print(f"Productos Activos:    {Producto.objects.filter(activo=True).count()}")
print(f"Stock Total:          {stock_total} unidades")
print(f"Lotes Activos:        {Lote.objects.filter(estado='disponible', cantidad_actual__gt=0, deleted_at__isnull=True).count()}")
print(f"Movimientos del Mes:  {movimientos_mes}")
print("=" * 80)

# Test endpoint
print("\n\nProbando endpoint de dashboard...")
from django.test import RequestFactory
from inventario.views import dashboard_resumen
from django.contrib.auth import get_user_model

User = get_user_model()
factory = RequestFactory()
admin = User.objects.filter(is_superuser=True).first()

if admin:
    request = factory.get('/api/dashboard/')
    request.user = admin
    
    try:
        response = dashboard_resumen(request)
        if response.status_code == 200:
            data = response.data
            print("✓ Endpoint funcionando correctamente")
            print(f"  - Total productos: {data['kpi']['total_productos']}")
            print(f"  - Stock total: {data['kpi']['stock_total']}")
            print(f"  - Lotes activos: {data['kpi']['lotes_activos']}")
            print(f"  - Movimientos mes: {data['kpi']['movimientos_mes']}")
            print(f"  - Últimos movimientos: {len(data['ultimos_movimientos'])}")
        else:
            print(f"✗ Error en endpoint: status {response.status_code}")
    except Exception as e:
        print(f"✗ Error al probar endpoint: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("VERIFICACIÓN COMPLETADA")
print("=" * 80)
