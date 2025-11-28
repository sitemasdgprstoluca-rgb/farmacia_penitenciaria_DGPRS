"""
Diagnóstico rápido de problemas del frontend
"""
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

import requests
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

User = get_user_model()
admin = User.objects.filter(username='admin').first()
token = str(RefreshToken.for_user(admin).access_token)
headers = {"Authorization": f"Bearer {token}"}
BASE = "http://127.0.0.1:8000/api"

print("="*60)
print("DIAGNÓSTICO DE ENDPOINTS PROBLEMÁTICOS")
print("="*60)

# 1. Dashboard gráficas
print("\n1. Dashboard Gráficas:")
try:
    r = requests.get(f"{BASE}/dashboard/graficas/", headers=headers, timeout=5)
    print(f"   Status: {r.status_code}")
    data = r.json()
    print(f"   Keys: {list(data.keys())}")
    print(f"   ¿Tiene consumo_mensual? {'consumo_mensual' in data}")
    print(f"   ¿Tiene stock_por_centro? {'stock_por_centro' in data}")
    print(f"   ¿Tiene requisiciones_por_estado? {'requisiciones_por_estado' in data}")
except Exception as e:
    print(f"   ERROR: {e}")

# 2. Reporte inventario
print("\n2. Reporte Inventario:")
try:
    r = requests.get(f"{BASE}/reportes/inventario/", headers=headers, timeout=5)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            print(f"   Registros: {len(data)}")
        else:
            print(f"   Keys: {list(data.keys())}")
            print(f"   Registros: {len(data.get('data', data.get('results', [])))}")
    else:
        print(f"   Error: {r.text[:200]}")
except Exception as e:
    print(f"   ERROR: {e}")

# 3. Hojas de recolección (PDF requisiciones)
print("\n3. Hojas de Recolección (listar):")
try:
    r = requests.get(f"{BASE}/hojas-recoleccion/", headers=headers, timeout=5)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        count = data.get('count', len(data.get('results', [])))
        print(f"   Count: {count}")
except Exception as e:
    print(f"   ERROR: {e}")

# 4. Requisiciones - descargar PDF (buscar una surtida)
print("\n4. Requisiciones - Verificar endpoint PDF:")
from core.models import Requisicion
req_surtida = Requisicion.objects.filter(estado='SURTIDA').first()
if req_surtida:
    print(f"   Requisición surtida: {req_surtida.folio} (ID: {req_surtida.id})")
    # Probar endpoint de hoja
    try:
        r = requests.get(f"{BASE}/requisiciones/{req_surtida.id}/descargar_hoja/", headers=headers, timeout=5)
        print(f"   Status descargar_hoja: {r.status_code}")
        if r.status_code != 200:
            print(f"   Error: {r.text[:200]}")
    except Exception as e:
        print(f"   ERROR: {e}")
else:
    print("   No hay requisiciones surtidas")

# 5. Trazabilidad PDF
print("\n5. Trazabilidad:")
from core.models import Producto
prod = Producto.objects.first()
if prod:
    try:
        r = requests.get(f"{BASE}/trazabilidad/{prod.clave}/", headers=headers, timeout=5)
        print(f"   Status trazabilidad/{prod.clave}/: {r.status_code}")
        # Probar PDF
        r2 = requests.get(f"{BASE}/trazabilidad/{prod.clave}/?format=pdf", headers=headers, timeout=5)
        print(f"   Status PDF: {r2.status_code}")
        if r2.status_code != 200:
            print(f"   Error PDF: {r2.text[:200]}")
    except Exception as e:
        print(f"   ERROR: {e}")

# 6. Auditoria exportar
print("\n6. Auditoría export:")
try:
    r = requests.get(f"{BASE}/auditoria/exportar/", headers=headers, timeout=5)
    print(f"   Status: {r.status_code}")
    print(f"   Content-Type: {r.headers.get('Content-Type', 'N/A')}")
except Exception as e:
    print(f"   ERROR: {e}")

print("\n" + "="*60)
