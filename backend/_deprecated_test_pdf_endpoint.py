"""
Test de endpoint de PDF de hojas de recolección
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
from core.models import Requisicion

User = get_user_model()
admin = User.objects.filter(username='admin').first()
token = str(RefreshToken.for_user(admin).access_token)
headers = {"Authorization": f"Bearer {token}"}
BASE = "http://127.0.0.1:8000/api"

print("="*60)
print("TEST PDF HOJAS DE RECOLECCIÓN")
print("="*60)

# Buscar requisición surtida/autorizada
req = Requisicion.objects.filter(estado__in=['autorizada', 'surtida', 'parcial']).first()
if not req:
    print("No hay requisiciones autorizadas/surtidas para probar")
    exit(1)

print(f"\nRequisición: {req.folio} (ID: {req.id}) - Estado: {req.estado}")

# Probar endpoint
print(f"\nProbando: GET /requisiciones/{req.id}/hoja-recoleccion/")
try:
    r = requests.get(f"{BASE}/requisiciones/{req.id}/hoja-recoleccion/", headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
    
    if r.status_code == 200:
        print(f"PDF Size: {len(r.content)} bytes")
        # Guardar para verificar
        with open('test_hoja.pdf', 'wb') as f:
            f.write(r.content)
        print("PDF guardado como test_hoja.pdf")
    else:
        print(f"Error: {r.text[:500]}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "="*60)
