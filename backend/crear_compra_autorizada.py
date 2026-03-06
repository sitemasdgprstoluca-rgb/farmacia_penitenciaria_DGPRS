#!/usr/bin/env python
"""Script para crear compra autorizada de prueba para medico_c21_2"""
import os
import django
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import CompraCajaChica, DetalleCompraCajaChica, Producto, Centro
from datetime import date

User = get_user_model()

# Obtener usuario medico_c21_2 (ID 387)
try:
    medico = User.objects.get(id=387)
    print(f"✓ Usuario encontrado: {medico.username} (ID: {medico.id})")
except User.DoesNotExist:
    print("✗ Usuario ID 387 no encontrado")
    sys.exit(1)

# Obtener centro
centro = medico.centro
if not centro:
    print("✗ Usuario no tiene centro asignado")
    sys.exit(1)
print(f"✓ Centro: {centro.nombre}")

# Obtener un producto cualquiera
producto = Producto.objects.first()
if not producto:
    print("✗ No hay productos en la base de datos")
    sys.exit(1)
print(f"✓ Producto: {producto.nombre}")

# Crear compra
compra = CompraCajaChica.objects.create(
    centro=centro,
    solicitante=medico,
    estado='autorizada',  # Directamente autorizada
    motivo_compra='Prueba para captura de recepción',
    proveedor_nombre='Proveedor de Prueba',
    subtotal=100.00,
    iva=16.00,
    total=116.00
)
print(f"✓ Compra creada: {compra.folio}")

# Crear detalle
detalle = DetalleCompraCajaChica.objects.create(
    compra=compra,
    producto=producto,
    descripcion_producto=producto.nombre,
    cantidad_solicitada=5,
    precio_unitario=100.00,
    importe=500.00
)
print(f"✓ Detalle agregado: {detalle.descripcion_producto} x {detalle.cantidad_solicitada}")

print(f"\n{'='*60}")
print(f"✅ COMPRA CREADA CON ÉXITO")
print(f"{'='*60}")
print(f"Folio: {compra.folio}")
print(f"Estado: {compra.estado}")
print(f"Solicitante: {medico.username} (ID: {medico.id})")
print(f"Centro: {centro.nombre}")
print(f"Total: ${compra.total}")
print(f"\n🎯 Ahora abre esta compra en el sistema y verás el formulario de captura")
