#!/usr/bin/env python
"""Test de filtros de reportes"""
import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
client = Client()

# Obtener usuario admin
admin = User.objects.filter(is_staff=True).first()
if not admin:
    admin = User.objects.first()
print(f"Usuario: {admin.username} (staff={admin.is_staff})")

# Login
client.force_login(admin)

# Test 1: Reporte Requisiciones con filtro 'todos'
print("\n" + "="*50)
print("TEST REPORTE REQUISICIONES (filtro: todos)")
print("="*50)
response = client.get('/api/reportes/requisiciones/', {'centro': 'todos'})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total requisiciones: {data.get('resumen', {}).get('total', 0)}")
    print(f"Filtro aplicado: {data.get('resumen', {}).get('filtro', 'N/A')}")
else:
    print(f"Error: {response.content[:200]}")

# Test 2: Reporte Requisiciones con filtro 'central'
print("\n" + "="*50)
print("TEST REPORTE REQUISICIONES (filtro: central)")
print("="*50)
response = client.get('/api/reportes/requisiciones/', {'centro': 'central'})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total requisiciones: {data.get('resumen', {}).get('total', 0)}")
    print(f"Filtro aplicado: {data.get('resumen', {}).get('filtro', 'N/A')}")

# Test 3: Reporte Movimientos con filtro 'central'  
print("\n" + "="*50)
print("TEST REPORTE MOVIMIENTOS (filtro: central)")
print("="*50)
response = client.get('/api/reportes/movimientos/', {
    'centro': 'central', 
    'fecha_inicio': '2026-01-01', 
    'fecha_fin': '2026-01-31'
})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    resumen = data.get('resumen', {})
    print(f"Total transacciones: {resumen.get('total_transacciones', 0)}")
    print(f"Entradas: {resumen.get('total_entradas', 0)} uds")
    print(f"Salidas: {resumen.get('total_salidas', 0)} uds")
    print(f"Filtro aplicado: {resumen.get('filtro', 'N/A')}")

# Test 4: Reporte Movimientos con filtro 'todos'  
print("\n" + "="*50)
print("TEST REPORTE MOVIMIENTOS (filtro: todos)")
print("="*50)
response = client.get('/api/reportes/movimientos/', {
    'centro': 'todos', 
    'fecha_inicio': '2026-01-01', 
    'fecha_fin': '2026-01-31'
})
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    resumen = data.get('resumen', {})
    print(f"Total transacciones: {resumen.get('total_transacciones', 0)}")
    print(f"Entradas: {resumen.get('total_entradas', 0)} uds")
    print(f"Salidas: {resumen.get('total_salidas', 0)} uds")
    print(f"Filtro aplicado: {resumen.get('filtro', 'N/A')}")

print("\n" + "="*50)
print("TODOS LOS TESTS COMPLETADOS")
print("="*50)
