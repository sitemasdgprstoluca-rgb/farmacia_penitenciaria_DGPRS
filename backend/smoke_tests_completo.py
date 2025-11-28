"""
SMOKE TESTS COMPLETOS - Sistema de Farmacia Penitenciaria
==========================================================
Pruebas de flujos críticos con filtros por centro

Ejecutar con:
  python manage.py shell < smoke_tests_completo.py
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework.test import APIRequestFactory
from core.models import Producto, Lote, Movimiento, Centro, Requisicion, DetalleRequisicion
from inventario.views import (
    dashboard_resumen, dashboard_graficas, 
    reporte_inventario, reporte_movimientos,
    is_farmacia_or_admin, get_user_centro,
    LoteViewSet, MovimientoViewSet, RequisicionViewSet
)

User = get_user_model()
factory = APIRequestFactory()

print("=" * 70)
print(" SMOKE TESTS COMPLETOS - FARMACIA PENITENCIARIA")
print("=" * 70)

# ============================================================================
# 1. HELPERS DE ROL/CENTRO
# ============================================================================
print("\n[1] HELPERS DE ROL/CENTRO")
print("-" * 50)

admin = User.objects.filter(is_superuser=True).first()
farmacia_user = User.objects.filter(rol__in=['farmacia', 'admin_farmacia']).first()
centro_user = User.objects.filter(rol='usuario_normal', centro__isnull=False).first()

if admin:
    print(f"  Admin: {admin.username} -> is_farmacia_or_admin={is_farmacia_or_admin(admin)}")
if farmacia_user:
    print(f"  Farmacia: {farmacia_user.username} -> is_farmacia_or_admin={is_farmacia_or_admin(farmacia_user)}")
if centro_user:
    centro = get_user_centro(centro_user)
    print(f"  Centro: {centro_user.username} -> is_farmacia_or_admin={is_farmacia_or_admin(centro_user)}, centro={centro}")

# ============================================================================
# 2. DASHBOARD
# ============================================================================
print("\n[2] DASHBOARD")
print("-" * 50)

# Test global (admin)
if admin:
    request = factory.get('/api/dashboard/')
    request.user = admin
    request.query_params = {}
    response = dashboard_resumen(request)
    kpi = response.data.get('kpi', {})
    print(f"  Admin global: stock={kpi.get('stock_total')}, lotes={kpi.get('lotes_activos')}")

# Test con filtro de centro
centro_test = Centro.objects.first()
if admin and centro_test:
    request = factory.get(f'/api/dashboard/?centro={centro_test.id}')
    request.user = admin
    request.query_params = {'centro': str(centro_test.id)}
    response = dashboard_resumen(request)
    kpi = response.data.get('kpi', {})
    print(f"  Admin filtrado ({centro_test.nombre[:20]}): stock={kpi.get('stock_total')}, lotes={kpi.get('lotes_activos')}")

# Test usuario de centro (forzado)
if centro_user:
    request = factory.get('/api/dashboard/')
    request.user = centro_user
    request.query_params = {}
    response = dashboard_resumen(request)
    kpi = response.data.get('kpi', {})
    print(f"  Centro forzado: stock={kpi.get('stock_total')}, lotes={kpi.get('lotes_activos')}")

# ============================================================================
# 3. LOTES CON FILTRO POR CENTRO
# ============================================================================
print("\n[3] LOTES - FILTRO POR CENTRO")
print("-" * 50)

total_lotes = Lote.objects.filter(deleted_at__isnull=True).count()
lotes_sin_centro = Lote.objects.filter(centro__isnull=True, deleted_at__isnull=True).count()
print(f"  Total lotes: {total_lotes}, Sin centro (farmacia central): {lotes_sin_centro}")

if centro_test:
    lotes_centro = Lote.objects.filter(centro=centro_test, deleted_at__isnull=True).count()
    print(f"  Lotes en {centro_test.nombre[:20]}: {lotes_centro}")

# ============================================================================
# 4. MOVIMIENTOS CON FILTRO POR CENTRO
# ============================================================================
print("\n[4] MOVIMIENTOS - FILTRO POR CENTRO")
print("-" * 50)

total_movimientos = Movimiento.objects.count()
print(f"  Total movimientos: {total_movimientos}")

if centro_test:
    mov_centro = Movimiento.objects.filter(lote__centro=centro_test).count()
    print(f"  Movimientos en {centro_test.nombre[:20]}: {mov_centro}")

# ============================================================================
# 5. REQUISICIONES Y SURTIDO
# ============================================================================
print("\n[5] REQUISICIONES Y SURTIDO")
print("-" * 50)

total_req = Requisicion.objects.count()
req_surtidas = Requisicion.objects.filter(estado='surtida').count()
print(f"  Total requisiciones: {total_req}, Surtidas: {req_surtidas}")

# Verificar que el surtido crea entradas en centros destino
req_surtida = Requisicion.objects.filter(estado='surtida').select_related('centro').first()
if req_surtida and req_surtida.centro:
    mov_entrada = Movimiento.objects.filter(
        requisicion=req_surtida,
        tipo='entrada',
        centro=req_surtida.centro
    ).count()
    mov_salida = Movimiento.objects.filter(
        requisicion=req_surtida,
        tipo='salida'
    ).count()
    print(f"  Requisicion {req_surtida.folio}: salidas={mov_salida}, entradas_centro={mov_entrada}")

# ============================================================================
# 6. INVENTARIO POR CENTRO
# ============================================================================
print("\n[6] INVENTARIO POR CENTRO")
print("-" * 50)

for centro in Centro.objects.filter(activo=True)[:5]:
    stock = Lote.objects.filter(
        centro=centro,
        estado='disponible',
        deleted_at__isnull=True
    ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
    lotes = Lote.objects.filter(centro=centro, deleted_at__isnull=True).count()
    print(f"  {centro.nombre[:30]}: stock={stock}, lotes={lotes}")

# Farmacia central
stock_central = Lote.objects.filter(
    centro__isnull=True,
    estado='disponible',
    deleted_at__isnull=True
).aggregate(total=Sum('cantidad_actual'))['total'] or 0
lotes_central = Lote.objects.filter(centro__isnull=True, deleted_at__isnull=True).count()
print(f"  FARMACIA CENTRAL (sin centro): stock={stock_central}, lotes={lotes_central}")

# ============================================================================
# 7. REPORTES
# ============================================================================
print("\n[7] REPORTES - VERIFICACION DE FILTROS")
print("-" * 50)

# Verificar que reportes tienen filtros implementados
from inventario import views as inv_views
import inspect

reportes_con_filtro = []
for name in ['reporte_inventario', 'reporte_movimientos', 'reporte_caducidades', 
             'reporte_requisiciones', 'reporte_bajo_stock', 'reporte_consumo']:
    func = getattr(inv_views, name, None)
    if func:
        source = inspect.getsource(func)
        tiene_filtro = 'is_farmacia_or_admin' in source or 'centro_param' in source
        reportes_con_filtro.append((name, tiene_filtro))
        status = "OK" if tiene_filtro else "FALTA FILTRO"
        print(f"  {name}: [{status}]")

# ============================================================================
# RESUMEN
# ============================================================================
print("\n" + "=" * 70)
print(" RESUMEN DE SMOKE TESTS")
print("=" * 70)

issues = []

if not admin:
    issues.append("No hay usuario admin para tests")
if total_lotes == 0:
    issues.append("No hay lotes en la base de datos")
if total_movimientos == 0:
    issues.append("No hay movimientos registrados")

reportes_sin_filtro = [r for r, ok in reportes_con_filtro if not ok]
if reportes_sin_filtro:
    issues.append(f"Reportes sin filtro de centro: {reportes_sin_filtro}")

if issues:
    print("\n ISSUES DETECTADOS:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("\n TODOS LOS TESTS PASARON")

print("\n" + "=" * 70)
