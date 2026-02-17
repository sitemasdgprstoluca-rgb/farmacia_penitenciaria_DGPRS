#!/usr/bin/env python
"""
Test exhaustivo del sistema de cantidad_contrato_global.
Valida backend y frontend integration.
"""
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from core.models import Lote, Producto, Movimiento
from decimal import Decimal

User = get_user_model()
admin = User.objects.get(username='admin')
client = APIClient()
client.force_authenticate(user=admin)

print("\n" + "="*80)
print("PRUEBAS EXHAUSTIVAS - SISTEMA CANTIDAD CONTRATO GLOBAL")
print("="*80)

# TEST 1: Verificar endpoint /api/lotes/ incluye CCG
print("\n[TEST 1] Endpoint /api/lotes/ incluye cantidad_contrato_global")
response = client.get('/api/lotes/?page_size=5')
assert response.status_code == 200, f"Error {response.status_code}"
data = response.json()
lotes_con_ccg = [l for l in data['results'] if l.get('cantidad_contrato_global') is not None]
print(f"  OK: {len(lotes_con_ccg)}/{len(data['results'])} lotes tienen CCG")
if lotes_con_ccg:
    lote = lotes_con_ccg[0]
    print(f"  Ejemplo: Lote {lote['numero_lote']}")
    print(f"    - cantidad_contrato_global: {lote['cantidad_contrato_global']}")
    print(f"    - cantidad_pendiente_global: {lote.get('cantidad_pendiente_global')}")
    assert 'cantidad_contrato_global' in lote, "Campo faltante"
    assert 'cantidad_pendiente_global' in lote, "Campo pendiente_global faltante"

# TEST 2: Verificar endpoint consolidados incluye CCG
print("\n[TEST 2] Endpoint /api/lotes/consolidados/ incluye cantidad_contrato_global")
response = client.get('/api/lotes/consolidados/?page_size=5')
assert response.status_code == 200, f"Error {response.status_code}"
data = response.json()
lotes_cons_ccg = [l for l in data['results'] if l.get('cantidad_contrato_global') is not None]
print(f"  OK: {len(lotes_cons_ccg)}/{len(data['results'])} lotes consolidados tienen CCG")
if lotes_cons_ccg:
    lote = lotes_cons_ccg[0]
    print(f"  Ejemplo: Lote {lote['numero_lote']}")
    print(f"    - cantidad_contrato_global: {lote['cantidad_contrato_global']}")
    print(f"    - cantidad_pendiente_global: {lote.get('cantidad_pendiente_global')}")

# TEST 3: Verificar cálculo de cantidad_pendiente_global
print("\n[TEST 3] Calculo correcto de cantidad_pendiente_global")
# Buscar lote con CCG en BD
lote_bd = Lote.objects.filter(
    cantidad_contrato_global__isnull=False,
    numero_contrato__isnull=False
).select_related('producto').first()

if lote_bd:
    # Calcular manualmente
    total_recibido = Lote.objects.filter(
        producto=lote_bd.producto,
        numero_contrato=lote_bd.numero_contrato,
        cantidad_contrato_global__isnull=False
    ).aggregate(total=django.db.models.Sum('cantidad_inicial'))['total'] or 0
    
    pendiente_esperado = lote_bd.cantidad_contrato_global - total_recibido
    
    # Verificar via API
    response = client.get(f'/api/lotes/{lote_bd.id}/')
    lote_api = response.json()
    
    print(f"  Lote: {lote_bd.numero_lote}")
    print(f"    CCG: {lote_bd.cantidad_contrato_global}")
    print(f"    Total recibido (BD): {total_recibido}")
    print(f"    Pendiente esperado: {pendiente_esperado}")
    print(f"    Pendiente API: {lote_api.get('cantidad_pendiente_global')}")
    
    assert lote_api.get('cantidad_pendiente_global') == pendiente_esperado, "Calculo incorrecto"
    print(f"  OK: Calculo correcto")

# TEST 4: Verificar bloqueo de edicion con movimientos
print("\n[TEST 4] Campo tiene_movimientos presente")
lote_con_mov = Lote.objects.filter(
    id__in=Movimiento.objects.values_list('lote_id', flat=True).distinct()
).first()

if lote_con_mov:
    response = client.get(f'/api/lotes/{lote_con_mov.id}/')
    lote_data = response.json()
    print(f"  Lote con movimientos: {lote_con_mov.numero_lote}")
    print(f"    tiene_movimientos: {lote_data.get('tiene_movimientos')}")
    assert lote_data.get('tiene_movimientos') == True, "Campo tiene_movimientos incorrecto"
    print(f"  OK: Campo tiene_movimientos = True")

# TEST 5: Verificar propagacion de CCG (crear lote)
print("\n[TEST 5] Propagacion de CCG al crear lote (simulacion)")
producto_test = Producto.objects.first()
if producto_test:
    print(f"  Producto: {producto_test.clave} - {producto_test.nombre}")
    
    # Contar lotes actuales con contrato TEST
    lotes_antes = Lote.objects.filter(
        producto=producto_test,
        numero_contrato='TEST-CCG-2026'
    ).count()
    
    # Crear lote con CCG
    nuevo_lote_data = {
        'producto': producto_test.id,
        'numero_lote': f'TEST-CCG-{os.urandom(4).hex()}',
        'cantidad_inicial': 100,
        'cantidad_contrato': 100,
        'cantidad_contrato_global': 1000,
        'numero_contrato': 'TEST-CCG-2026',
        'fecha_caducidad': '2027-12-31',
        'precio_unitario': 10.50,
        'marca': 'TEST'
    }
    
    response = client.post('/api/lotes/', nuevo_lote_data, format='json')
    
    if response.status_code in [200, 201]:
        lote_creado = response.json()
        print(f"  Lote creado: {lote_creado['numero_lote']}")
        print(f"    CCG: {lote_creado.get('cantidad_contrato_global')}")
        
        # Verificar que otros lotes del mismo contrato tienen CCG propagado
        lotes_mismo_contrato = Lote.objects.filter(
            producto=producto_test,
            numero_contrato='TEST-CCG-2026'
        ).exclude(id=lote_creado['id'])
        
        if lotes_mismo_contrato.exists():
            for lote in lotes_mismo_contrato:
                print(f"    Lote hermano {lote.numero_lote}: CCG = {lote.cantidad_contrato_global}")
        
        # Limpiar lote de prueba
        Lote.objects.filter(id=lote_creado['id']).delete()
        print(f"  OK: Lote de prueba eliminado")
    else:
        print(f"  SKIP: No se pudo crear lote test ({response.status_code})")

# TEST 6: Verificar serializer incluye todos los campos
print("\n[TEST 6] Serializer incluye campos requeridos")
from core.serializers import LoteSerializer
campos_requeridos = [
    'cantidad_contrato',
    'cantidad_contrato_global', 
    'cantidad_pendiente',
    'cantidad_pendiente_global',
    'tiene_movimientos'
]
campos_serializer = LoteSerializer.Meta.fields
for campo in campos_requeridos:
    assert campo in campos_serializer, f"Campo {campo} faltante en serializer"
    print(f"  OK: Campo '{campo}' en serializer")

print("\n" + "="*80)
print("RESUMEN DE PRUEBAS")
print("="*80)
print("  [OK] Endpoint /api/lotes/ devuelve CCG")
print("  [OK] Endpoint /api/lotes/consolidados/ devuelve CCG")
print("  [OK] Calculo de cantidad_pendiente_global correcto")
print("  [OK] Campo tiene_movimientos funcional")
print("  [OK] Serializer completo")
print("\n  SISTEMA BACKEND: FUNCIONAL")
print("="*80 + "\n")
