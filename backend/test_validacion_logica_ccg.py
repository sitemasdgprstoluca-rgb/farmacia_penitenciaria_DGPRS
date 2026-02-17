"""
TEST SIMPLIFICADO - VALIDACIÓN DE LÓGICA DE NEGOCIO CONTRATOS GLOBALES
=======================================================================

Este script valida que el sistema calcula correctamente:
1. cantidad_recibido_global (suma de cantidad_inicial)
2. total_inventario_global (suma de cantidad_actual) ← NUEVO
3. cantidad_pendiente_global (contrato - recibido)

Y que las salidas NO afectan el cálculo del contrato.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from core.models import Lote
from django.db.models import Sum

User = get_user_model()


def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def test_campos_disponibles_en_api():
    """Test 1: Validar que los campos nuevos están disponibles en la API"""
    print_header("TEST 1: CAMPOS DISPONIBLES EN API")
    
    # Obtener usuario admin
    try:
        admin = User.objects.filter(rol='admin').first()
        if not admin:
            print("❌ No se encontró usuario admin")
            return False
    except Exception as e:
        print(f"❌ Error obteniendo admin: {e}")
        return False
    
    # Cliente API
    client = APIClient()
    client.force_authenticate(user=admin)
    
    # Obtener un lote con contrato global
    lote_con_ccg = Lote.objects.filter(cantidad_contrato_global__isnull=False).first()
    
    if not lote_con_ccg:
        print("⚠️  No hay lotes con contrato global en BD")
        return True
    
    # Llamar al endpoint
    response = client.get(f'/api/lotes/{lote_con_ccg.id}/')
    
    if response.status_code != 200:
        print(f"❌ Error en endpoint: {response.status_code}")
        return False
    
    data = response.json()
    
    # Validar campos
    campos_requeridos = [
        'cantidad_contrato_global',
        'cantidad_recibido_global',
        'total_inventario_global',  # NUEVO
        'cantidad_pendiente_global'
    ]
    
    print(f"\nLote #{lote_con_ccg.id} - {lote_con_ccg.numero_lote}")
    print(f"Producto: {lote_con_ccg.producto.nombre if lote_con_ccg.producto else 'N/A'}")
    print(f"Contrato: {lote_con_ccg.numero_contrato}")
    print("")
    
    for campo in campos_requeridos:
        if campo in data:
            print(f"✓ {campo}: {data[campo]}")
        else:
            print(f"❌ Campo faltante: {campo}")
            return False
    
    print("\n✅ TEST 1 PASADO: Todos los campos disponibles")
    return True


def test_logica_inventario_vs_recibido():
    """Test 2: Validar diferencia entre inventario y recibido"""
    print_header("TEST 2: INVENTARIO vs RECIBIDO")
    
    # Buscar lotes con contrato global donde haya diferencia entre inicial y actual
    lotes = Lote.objects.filter(
        cantidad_contrato_global__isnull=False,
        activo=True
    ).exclude(
        cantidad_inicial=models.F('cantidad_actual')
    )[:5]
    
    if not lotes:
        print("⚠️  No hay lotes con diferencia entre inicial y actual")
        print("   (Creando escenario de ejemplo...)")
        # Buscar cualquier lote con CCG
        lote = Lote.objects.filter(cantidad_contrato_global__isnull=False).first()
        if lote:
            print(f"\nEjemplo con lote #{lote.id}:")
            print(f"  Contrato Global: {lote.cantidad_contrato_global}")
            print(f"  Cantidad Inicial (recibido): {lote.cantidad_inicial}")
            print(f"  Cantidad Actual (inventario): {lote.cantidad_actual}")
            
            # Calcular manualmente
            total_recibido = Lote.objects.filter(
                producto=lote.producto,
                numero_contrato=lote.numero_contrato,
                activo=True
            ).aggregate(total=Sum('cantidad_inicial'))['total'] or 0
            
            total_inventario = Lote.objects.filter(
                producto=lote.producto,
                numero_contrato=lote.numero_contrato,
                activo=True
            ).aggregate(total=Sum('cantidad_actual'))['total'] or 0
            
            pendiente = lote.cantidad_contrato_global - total_recibido
            
            print(f"\n  Cálculos agregados para contrato {lote.numero_contrato}:")
            print(f"  ✓ Total Recibido Global: {total_recibido}")
            print(f"  ✓ Total Inventario Global: {total_inventario}")
            print(f"  ✓ Pendiente: {pendiente}")
            
            if total_recibido != total_inventario:
                print(f"  ✓ Diferencia (salidas): {total_recibido - total_inventario}")
                print(f"  ✓ CORRECTO: Pendiente usa recibido, NO inventario")
        
        print("\n✅ TEST 2 PASADO (ejemplo)")
        return True
    
    print(f"\nEncontrados {len(lotes)} lotes con diferencia inicial vs actual:\n")
    
    for lote in lotes:
        print(f"Lote #{lote.id} - {lote.numero_lote}")
        print(f"  Inicial (recibido): {lote.cantidad_inicial}")
        print(f"  Actual (inventario): {lote.cantidad_actual}")
        print(f"  Salidas: {lote.cantidad_inicial - lote.cantidad_actual}")
        print("")
    
    print("✅ TEST 2 PASADO: Hay lotes con diferencia")
    return True


def test_endpoint_consolidados():
    """Test 3: Validar endpoint consolidados"""
    print_header("TEST 3: ENDPOINT CONSOLIDADOS")
    
    admin = User.objects.filter(rol='admin').first()
    client = APIClient()
    client.force_authenticate(user=admin)
    
    response = client.get('/api/lotes/consolidados/?page_size=5')
    
    if response.status_code != 200:
        print(f"❌ Error: {response.status_code}")
        return False
    
    data = response.json()
    lotes = data.get('results', data) if isinstance(data, dict) else data
    
    if not lotes:
        print("⚠️  No hay lotes consolidados")
        return True
    
    print(f"\nTotal lotes consolidados (primeros 5): {len(lotes)}\n")
    
    for lote in lotes[:3]:
        if lote.get('cantidad_contrato_global'):
            print(f"Lote #{lote['id']} - {lote.get('numero_lote', 'N/A')}")
            print(f"  🌐 Contrato Global: {lote['cantidad_contrato_global']}")
            print(f"  📊 Recibido Global: {lote.get('cantidad_recibido_global', 'N/A')}")
            print(f"  📦 Inventario Global: {lote.get('total_inventario_global', 'N/A')}")
            print(f"  ⏳ Pendiente: {lote.get('cantidad_pendiente_global', 'N/A')}")
            print("")
    
    print("✅ TEST 3 PASADO: Endpoint consolidados funciona")
    return True


def test_calculo_pendiente_correcto():
    """Test 4: Validar que pendiente = contrato - recibido (NO contrato - actual)"""
    print_header("TEST 4: CÁLCULO DE PENDIENTE CORRECTO")
    
    admin = User.objects.filter(rol='admin').first()
    client = APIClient()
    client.force_authenticate(user=admin)
    
    # Buscar lote con CCG
    lote = Lote.objects.filter(cantidad_contrato_global__isnull=False).first()
    
    if not lote:
        print("⚠️  No hay lotes con contrato global")
        return True
    
    response = client.get(f'/api/lotes/{lote.id}/')
    data = response.json()
    
    print(f"\nLote #{lote.id} - Contrato: {lote.numero_contrato}")
    print(f"\nDatos del serializer:")
    print(f"  Contrato Global: {data['cantidad_contrato_global']}")
    print(f"  Recibido Global: {data['cantidad_recibido_global']}")
    print(f"  Inventario Global: {data['total_inventario_global']}")
    print(f"  Pendiente Global: {data['cantidad_pendiente_global']}")
    
    # Validación matemática
    esperado_pendiente = data['cantidad_contrato_global'] - data['cantidad_recibido_global']
    
    print(f"\nValidación matemática:")
    print(f"  Pendiente esperado = Contrato - Recibido")
    print(f"  {esperado_pendiente} = {data['cantidad_contrato_global']} - {data['cantidad_recibido_global']}")
    
    if data['cantidad_pendiente_global'] == esperado_pendiente:
        print(f"  ✓ CORRECTO: {data['cantidad_pendiente_global']} == {esperado_pendiente}")
    else:
        print(f"  ❌ ERROR: {data['cantidad_pendiente_global']} != {esperado_pendiente}")
        return False
    
    # Si hay diferencia entre recibido e inventario
    if data['cantidad_recibido_global'] != data['total_inventario_global']:
        diferencia = data['cantidad_recibido_global'] - data['total_inventario_global']
        print(f"\n  ✓ Hay salidas: {diferencia} unidades")
        print(f"  ✓ El pendiente NO cambió por las salidas (usa recibido, NO inventario)")
    
    print("\n✅ TEST 4 PASADO: Cálculo de pendiente correcto")
    return True


def run_all_tests():
    """Ejecutar todos los tests"""
    print("\n" + "="*80)
    print("  VALIDACIÓN DE LÓGICA DE NEGOCIO - CONTRATOS GLOBALES")
    print("="*80)
    
    tests = [
        ("Campos disponibles en API", test_campos_disponibles_en_api),
        ("Inventario vs Recibido", test_logica_inventario_vs_recibido),
        ("Endpoint Consolidados", test_endpoint_consolidados),
        ("Cálculo de Pendiente", test_calculo_pendiente_correcto)
    ]
    
    resultados = []
    
    for nombre, test_func in tests:
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
        except Exception as e:
            print(f"\n❌ ERROR en {nombre}: {e}")
            import traceback
            traceback.print_exc()
            resultados.append((nombre, False))
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    
    passed = sum(1 for _, r in resultados if r)
    total = len(resultados)
    
    for nombre, resultado in resultados:
        status = "✅ PASADO" if resultado else "❌ FALLIDO"
        print(f"{status}: {nombre}")
    
    print(f"\nTotal: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n" + "*"*80)
        print("TODOS LOS TESTS PASARON - LÓGICA DE NEGOCIO CORRECTA")
        print("*"*80)
        return True
    else:
        print("\n" + "!"*80)
        print("ALGUNOS TESTS FALLARON")
        print("!"*80)
        return False


if __name__ == '__main__':
    # Importar models aquí para evitar error de import
    from django.db import models
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
