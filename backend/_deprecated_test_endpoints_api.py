import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import force_authenticate
from inventario.views import LoteViewSet, ProductoViewSet, dashboard_resumen

User = get_user_model()

print('='*60)
print('TEST DE ENDPOINTS API')
print('='*60)

factory = RequestFactory()
admin = User.objects.filter(is_superuser=True).first()

# Test LoteViewSet
print('\n1. LoteViewSet.list()')
request = factory.get('/api/lotes/')
request.user = admin
request.query_params = {}

view = LoteViewSet.as_view({'get': 'list'})
response = view(request)

print(f'   Status: {response.status_code}')
if response.status_code == 200:
    data = response.data
    count = data.get('count', len(data.get('results', data)))
    print(f'   Total lotes: {count}')
    if 'results' in data and data['results']:
        print(f'   Primer lote: {data["results"][0].get("numero_lote", "N/A")}')
else:
    print(f'   ERROR: {response.data}')

# Test ProductoViewSet
print('\n2. ProductoViewSet.list()')
request = factory.get('/api/productos/')
request.user = admin
request.query_params = {}

view = ProductoViewSet.as_view({'get': 'list'})
response = view(request)

print(f'   Status: {response.status_code}')
if response.status_code == 200:
    data = response.data
    count = data.get('count', len(data.get('results', data)))
    print(f'   Total productos: {count}')
else:
    print(f'   ERROR: {response.data}')

# Test Dashboard
print('\n3. dashboard_resumen()')
from rest_framework.request import Request
request = factory.get('/api/dashboard/')
request.user = admin
request = Request(request)

response = dashboard_resumen(request)

print(f'   Status: {response.status_code}')
if response.status_code == 200:
    data = response.data
    kpi = data.get('kpi', {})
    print(f'   KPIs:')
    print(f'     - total_productos: {kpi.get("total_productos")}')
    print(f'     - stock_total: {kpi.get("stock_total")}')
    print(f'     - lotes_activos: {kpi.get("lotes_activos")}')
    print(f'     - movimientos_mes: {kpi.get("movimientos_mes")}')
else:
    print(f'   ERROR: {response.data}')

print('\n' + '='*60)
print('DIAGNÓSTICO COMPLETADO')
print('='*60)
