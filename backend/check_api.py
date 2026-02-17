#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
admin = User.objects.get(username='admin')

client = APIClient()
client.force_authenticate(user=admin)

# Test endpoint normal
print("\n=== TEST ENDPOINT /api/lotes/ ===")
response = client.get('/api/lotes/?page_size=2')
if response.status_code == 200:
    data = response.json()
    if data['results']:
        lote = data['results'][0]
        print(f"Lote: {lote['numero_lote']}")
        print(f"cantidad_contrato_global: {lote.get('cantidad_contrato_global', 'NO EXISTE')}")
        if 'cantidad_contrato_global' in lote:
            print("OK: Campo existe en endpoint normal")
        else:
            print("ERROR: Campo NO existe en endpoint normal")
            print(f"Campos: {list(lote.keys())}")
else:
    print(f"ERROR: {response.status_code}")

# Test endpoint consolidados
print("\n=== TEST ENDPOINT /api/lotes/consolidados/ ===")
response = client.get('/api/lotes/consolidados/?page_size=2')
if response.status_code == 200:
    data = response.json()
    if data['results']:
        lote = data['results'][0]
        print(f"Lote: {lote['numero_lote']}")
        print(f"cantidad_contrato_global: {lote.get('cantidad_contrato_global', 'NO EXISTE')}")
        if 'cantidad_contrato_global' in lote:
            print("OK: Campo existe en endpoint consolidados")
        else:
            print("ERROR: Campo NO existe en endpoint consolidados")
else:
    print(f"ERROR: {response.status_code}")
