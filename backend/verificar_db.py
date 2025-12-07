#!/usr/bin/env python
"""Script para verificar y crear datos de prueba"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from core.models import User, Centro, Producto, Lote
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import timedelta

print("🔍 Verificando base de datos...")

# Verificar usuario admin
try:
    admin = User.objects.get(username='admin')
    print(f"✅ Usuario admin existe: {admin.username}")
except User.DoesNotExist:
    print("❌ Usuario admin NO existe")

# Verificar tablas
print(f"\n📊 Estadísticas:")
print(f"   - Usuarios: {User.objects.count()}")
print(f"   - Centros: {Centro.objects.count()}")
print(f"   - Productos: {Producto.objects.count()}")
print(f"   - Lotes: {Lote.objects.count()}")

# Crear datos de prueba si no existen
if Centro.objects.count() == 0:
    print("\n🔧 Creando centro de prueba...")
    Centro.objects.create(
        nombre='Centro Penitenciario Norte',
        direccion='Av. Principal #123',
        activo=True
    )
    print("✅ Centro creado")

if Producto.objects.count() == 0:
    print("\n🔧 Creando productos de prueba...")
    Producto.objects.create(
        codigo_barras='PARACET500',
        nombre='Paracetamol 500mg',
        descripcion='Paracetamol tabletas 500mg',
        unidad_medida='pieza',
        categoria='medicamento',
        stock_minimo=100,
        activo=True
    )
    Producto.objects.create(
        codigo_barras='IBUPRO400',
        nombre='Ibuprofeno 400mg',
        descripcion='Ibuprofeno tabletas 400mg',
        unidad_medida='pieza',
        categoria='medicamento',
        stock_minimo=100,
        activo=True
    )
    print("✅ Productos creados")

print("\n✅ Base de datos verificada y lista")
