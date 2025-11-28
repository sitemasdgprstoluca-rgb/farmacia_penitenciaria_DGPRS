import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

print('='*60)
print('TEST API CON CLIENTE DJANGO')
print('='*60)

client = Client()

# Login como admin
admin = User.objects.filter(is_superuser=True).first()
print(f'\nUsuario: {admin.username}')

# Login y obtener token
response = client.post('/api/token/', {
    'username': 'admin',
    'password': 'admin123'  # Ajustar si es diferente
}, content_type='application/json')

print(f'Login status: {response.status_code}')

if response.status_code == 200:
    data = response.json()
    token = data.get('access')
    print(f'Token obtenido: {token[:50]}...')
    
    # Probar endpoint de lotes
    response = client.get('/api/lotes/', HTTP_AUTHORIZATION=f'Bearer {token}')
    print(f'\nGET /api/lotes/')
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        print(f'Count: {data.get("count", len(data))}')
        results = data.get('results', data)
        if results:
            print(f'Primer lote: {results[0].get("numero_lote")}')
    else:
        print(f'Error: {response.content}')
    
    # Probar dashboard
    response = client.get('/api/dashboard/', HTTP_AUTHORIZATION=f'Bearer {token}')
    print(f'\nGET /api/dashboard/')
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        kpi = data.get('kpi', {})
        print(f'KPIs: productos={kpi.get("total_productos")}, stock={kpi.get("stock_total")}, lotes={kpi.get("lotes_activos")}')
    else:
        print(f'Error: {response.content}')

else:
    print(f'Error login: {response.content}')
    print('\nProbando con token directo del admin...')
    
    # Force authenticate
    client.force_login(admin)
    
    response = client.get('/api/lotes/')
    print(f'\nGET /api/lotes/ (force_login)')
    print(f'Status: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        print(f'Count: {data.get("count", len(data))}')
    else:
        print(f'Error: {response.content[:500]}')
