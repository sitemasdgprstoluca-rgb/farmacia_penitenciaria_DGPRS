"""
Smoke tests para verificar filtrado por centro en dashboard
"""
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from inventario.views import dashboard_resumen, dashboard_graficas
from farmacia.models import Centro, Lote, Producto, Movimiento
from rest_framework.test import APIRequestFactory

User = get_user_model()

print('=== SMOKE TESTS: Dashboard con filtro por centro ===')
print()

# Obtener usuarios de prueba
admin = User.objects.filter(is_superuser=True).first()
centro_user = User.objects.filter(rol='usuario_normal').first()

if not admin:
    print('ERROR: No hay usuario admin para test')
else:
    print(f'Admin: {admin.username} (superuser={admin.is_superuser})')

if not centro_user:
    print('ERROR: No hay usuario de centro para test')
else:
    centro_obj = getattr(centro_user, 'centro', None)
    print(f'Centro user: {centro_user.username} (centro={centro_obj})')

# Test 1: Dashboard resumen sin filtro (admin)
print()
print('--- Test 1: dashboard_resumen admin sin filtro ---')
factory = APIRequestFactory()
request = factory.get('/api/dashboard/')
request.user = admin
request.query_params = {}
try:
    response = dashboard_resumen(request)
    print(f'Status: {response.status_code}')
    kpis = response.data.get('kpi', {})
    print(f'KPIs: productos={kpis.get("total_productos")}, stock={kpis.get("stock_total")}, lotes={kpis.get("lotes_activos")}')
except Exception as e:
    print(f'Error: {e}')

# Test 2: Dashboard resumen con filtro de centro (admin)
print()
print('--- Test 2: dashboard_resumen admin con ?centro=ID ---')
centro = Centro.objects.first()
if centro:
    request = factory.get(f'/api/dashboard/?centro={centro.id}')
    request.user = admin
    request.query_params = {'centro': str(centro.id)}
    try:
        response = dashboard_resumen(request)
        print(f'Status: {response.status_code}')
        print(f'Centro filtrado: {centro.nombre} (id={centro.id})')
        kpis = response.data.get('kpi', {})
        print(f'KPIs filtrados: productos={kpis.get("total_productos")}, stock={kpis.get("stock_total")}, lotes={kpis.get("lotes_activos")}')
    except Exception as e:
        print(f'Error: {e}')
else:
    print('No hay centros en la BD para probar filtro')

# Test 3: Dashboard graficas con cache
print()
print('--- Test 3: dashboard_graficas con cache ---')
request = factory.get('/api/dashboard/graficas/')
request.user = admin
request.query_params = {}
try:
    response = dashboard_graficas(request)
    print(f'Status: {response.status_code}')
    data = response.data
    mov_dias = data.get('movimientos_por_dia', {})
    bajo_stock = data.get('productos_bajo_stock', [])
    print(f'Movimientos por dia: {len(mov_dias)} dias')
    print(f'Productos bajo stock: {len(bajo_stock)} productos')
except Exception as e:
    print(f'Error: {e}')

# Test 4: Usuario de centro (forzado a su centro)
print()
print('--- Test 4: dashboard_resumen usuario de centro (forzado) ---')
if centro_user:
    request = factory.get('/api/dashboard/')
    request.user = centro_user
    request.query_params = {}
    try:
        response = dashboard_resumen(request)
        print(f'Status: {response.status_code}')
        kpis = response.data.get('kpi', {})
        print(f'KPIs (solo su centro): productos={kpis.get("total_productos")}, stock={kpis.get("stock_total")}, lotes={kpis.get("lotes_activos")}')
    except Exception as e:
        print(f'Error: {e}')

print()
print('=== SMOKE TESTS COMPLETADOS ===')
