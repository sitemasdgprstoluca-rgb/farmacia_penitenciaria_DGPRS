#!/usr/bin/env python
"""Test directo del API - sin pytest, solo llamada HTTP"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from core.models import Lote

User = get_user_model()

# Crear cliente y autenticar
client = APIClient()
try:
    admin = User.objects.get(username='admin')
except:
    print("ERROR: No existe usuario admin - crea uno primero")
    sys.exit(1)

client.force_authenticate(user=admin)

# Llamar al endpoint consolidados
print("\nLlamando GET /api/lotes/consolidados/")
response = client.get('/api/lotes/consolidados/')

if response.status_code != 200:
    print(f"ERROR: {response.status_code}")
    print(response.json())
    sys.exit(1)

data = response.json()
print(f"OK: {response.status_code}")
print(f"Total lotes: {data['count']}")

# Buscar lotes del contrato CB/A/37/2025
lotes_contrato = [l for l in data['results'] if l.get('numero_contrato') == 'CB/A/37/2025']

if not lotes_contrato:
    print("\nNo hay lotes del contrato CB/A/37/2025 en la primera página")
    print("Buscando cualquier lote con CCG...")
    lotes_contrato = [l for l in data['results'] if l.get('cantidad_contrato_global') is not None]

print(f"\nLotes encontrados con CCG: {len(lotes_contrato)}")

for i, lote in enumerate(lotes_contrato[:3], 1):
    print(f"\n{i}. Lote: {lote['numero_lote']}")
    print(f"   Contrato: {lote.get('numero_contrato', 'N/A')}")
    print(f"   CCG: {lote.get('cantidad_contrato_global', 'NO EXISTE CAMPO')}")
    print(f"   Pendiente Global: {lote.get('cantidad_pendiente_global', 'NO EXISTE CAMPO')}")

# Verificar si el campo existe en la respuesta
primer_lote = data['results'][0] if data['results'] else {}
if 'cantidad_contrato_global' in primer_lote:
    print("\nOK: El campo cantidad_contrato_global SI existe en la respuesta del API")
else:
    print("\nERROR: El campo cantidad_contrato_global NO existe en la respuesta del API")
    print(f"Campos disponibles: {list(primer_lote.keys())}")
