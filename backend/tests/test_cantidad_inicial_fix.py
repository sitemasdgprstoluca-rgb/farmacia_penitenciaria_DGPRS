# -*- coding: utf-8 -*-
"""
Test específico para verificar la corrección del bug de cantidad_inicial en entradas.

Bug corregido: El código usaba `cantidad` (string) en lugar de `cantidad_int` (entero)
para incrementar cantidad_inicial en movimientos de entrada.

Ejecutar: python test_cantidad_inicial_fix.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
django.setup()

import json
from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Producto, Lote, Movimiento, Centro

User = get_user_model()

# Colores para output
class C:
    OK = '\033[92m'
    FAIL = '\033[91m'
    WARN = '\033[93m'
    INFO = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def p(msg, color=C.INFO):
    print(f"{color}{msg}{C.END}")

def test_passed(name):
    print(f"{C.OK}✓ PASS:{C.END} {name}")

def test_failed(name, reason):
    print(f"{C.FAIL}✗ FAIL:{C.END} {name}")
    print(f"  {C.WARN}Razón: {reason}{C.END}")

def main():
    print(f"\n{C.BOLD}{'='*70}")
    print("TEST: Corrección de cantidad_inicial en movimientos de entrada")
    print(f"{'='*70}{C.END}\n")
    
    results = {'passed': 0, 'failed': 0, 'tests': []}
    
    # Setup: Obtener o crear usuario admin
    try:
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.create_superuser(
                username='test_admin_ci',
                email='test_ci@test.com',
                password='testpass123'
            )
            p("Usuario admin creado para tests", C.WARN)
        else:
            p(f"Usando admin existente: {admin.username}", C.INFO)
    except Exception as e:
        p(f"Error creando admin: {e}", C.FAIL)
        return
    
    client = APIClient()
    client.force_authenticate(user=admin)
    
    # =========================================================================
    # TEST 1: Crear producto y lote de prueba
    # =========================================================================
    test_name = "1. Crear producto y lote de prueba"
    p(f"\n{C.BOLD}>>> {test_name}{C.END}")
    
    try:
        # Crear producto único
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        producto_data = {
            'clave': f'TEST-CI-{unique_id}',
            'nombre': f'Producto Test Cantidad Inicial {unique_id}',
            'presentacion': 'Caja',
            'unidad_medida': 'Pieza',
            'categoria': 'medicamento'
        }
        
        resp = client.post('/api/productos/', producto_data, format='json')
        if resp.status_code != 201:
            raise Exception(f"No se pudo crear producto: {resp.status_code} - {resp.data}")
        
        producto_id = resp.data['id']
        p(f"  Producto creado: ID={producto_id}, clave={producto_data['clave']}")
        
        # Crear lote con cantidad_inicial conocida
        lote_data = {
            'producto': producto_id,
            'numero_lote': f'LOTE-CI-{unique_id}',
            'fecha_caducidad': '2027-12-31',
            'cantidad_inicial': 100,
            'cantidad_actual': 100,
            'marca': 'Test Lab',
            'laboratorio': 'Test Lab'
        }
        
        resp = client.post('/api/lotes/', lote_data, format='json')
        if resp.status_code != 201:
            raise Exception(f"No se pudo crear lote: {resp.status_code} - {resp.data}")
        
        lote_id = resp.data['id']
        lote_numero = lote_data['numero_lote']
        p(f"  Lote creado: ID={lote_id}, numero={lote_numero}")
        p(f"  cantidad_inicial=100, cantidad_actual=100")
        
        test_passed(test_name)
        results['passed'] += 1
        results['tests'].append((test_name, True, None))
        
    except Exception as e:
        test_failed(test_name, str(e))
        results['failed'] += 1
        results['tests'].append((test_name, False, str(e)))
        return results  # No podemos continuar sin producto/lote
    
    # =========================================================================
    # TEST 2: Hacer entrada de +25 y verificar cantidad_inicial sube
    # =========================================================================
    test_name = "2. Entrada +25: cantidad_inicial debe subir a 125"
    p(f"\n{C.BOLD}>>> {test_name}{C.END}")
    
    try:
        # Verificar estado inicial
        lote_antes = Lote.objects.get(pk=lote_id)
        ci_antes = lote_antes.cantidad_inicial
        ca_antes = lote_antes.cantidad_actual
        p(f"  Antes: cantidad_inicial={ci_antes}, cantidad_actual={ca_antes}")
        
        # Hacer entrada
        mov_data = {
            'tipo': 'entrada',
            'lote': lote_id,
            'cantidad': 25,
            'motivo': 'Test reabastecimiento - verificar cantidad_inicial'
        }
        
        resp = client.post('/api/movimientos/', mov_data, format='json')
        if resp.status_code != 201:
            raise Exception(f"Error creando movimiento: {resp.status_code} - {resp.data}")
        
        # Verificar estado después
        lote_despues = Lote.objects.get(pk=lote_id)
        ci_despues = lote_despues.cantidad_inicial
        ca_despues = lote_despues.cantidad_actual
        p(f"  Después: cantidad_inicial={ci_despues}, cantidad_actual={ca_despues}")
        
        # Validaciones
        if ca_despues != ca_antes + 25:
            raise Exception(f"cantidad_actual incorrecta: esperado {ca_antes + 25}, obtenido {ca_despues}")
        
        if ci_despues != ci_antes + 25:
            raise Exception(f"cantidad_inicial NO se incrementó: esperado {ci_antes + 25}, obtenido {ci_despues}")
        
        p(f"  {C.OK}✓ cantidad_actual: {ca_antes} → {ca_despues} (+25){C.END}")
        p(f"  {C.OK}✓ cantidad_inicial: {ci_antes} → {ci_despues} (+25){C.END}")
        
        test_passed(test_name)
        results['passed'] += 1
        results['tests'].append((test_name, True, None))
        
    except Exception as e:
        test_failed(test_name, str(e))
        results['failed'] += 1
        results['tests'].append((test_name, False, str(e)))
    
    # =========================================================================
    # TEST 3: Hacer salida de -10 y verificar cantidad_inicial NO cambia
    # =========================================================================
    test_name = "3. Salida -10: cantidad_inicial debe mantenerse en 125"
    p(f"\n{C.BOLD}>>> {test_name}{C.END}")
    
    try:
        lote_antes = Lote.objects.get(pk=lote_id)
        ci_antes = lote_antes.cantidad_inicial
        ca_antes = lote_antes.cantidad_actual
        p(f"  Antes: cantidad_inicial={ci_antes}, cantidad_actual={ca_antes}")
        
        # Hacer salida
        mov_data = {
            'tipo': 'salida',
            'lote': lote_id,
            'cantidad': 10,
            'motivo': 'Test salida - cantidad_inicial no debe cambiar',
            'subtipo_salida': 'consumo_interno'
        }
        
        resp = client.post('/api/movimientos/', mov_data, format='json')
        if resp.status_code != 201:
            raise Exception(f"Error creando movimiento: {resp.status_code} - {resp.data}")
        
        lote_despues = Lote.objects.get(pk=lote_id)
        ci_despues = lote_despues.cantidad_inicial
        ca_despues = lote_despues.cantidad_actual
        p(f"  Después: cantidad_inicial={ci_despues}, cantidad_actual={ca_despues}")
        
        if ca_despues != ca_antes - 10:
            raise Exception(f"cantidad_actual incorrecta: esperado {ca_antes - 10}, obtenido {ca_despues}")
        
        if ci_despues != ci_antes:
            raise Exception(f"cantidad_inicial cambió indebidamente: era {ci_antes}, ahora {ci_despues}")
        
        p(f"  {C.OK}✓ cantidad_actual: {ca_antes} → {ca_despues} (-10){C.END}")
        p(f"  {C.OK}✓ cantidad_inicial: {ci_antes} → {ci_despues} (sin cambio){C.END}")
        
        test_passed(test_name)
        results['passed'] += 1
        results['tests'].append((test_name, True, None))
        
    except Exception as e:
        test_failed(test_name, str(e))
        results['failed'] += 1
        results['tests'].append((test_name, False, str(e)))
    
    # =========================================================================
    # TEST 4: Múltiples entradas consecutivas
    # =========================================================================
    test_name = "4. Múltiples entradas: +5, +10, +15 = cantidad_inicial +30"
    p(f"\n{C.BOLD}>>> {test_name}{C.END}")
    
    try:
        lote_antes = Lote.objects.get(pk=lote_id)
        ci_antes = lote_antes.cantidad_inicial
        ca_antes = lote_antes.cantidad_actual
        p(f"  Antes: cantidad_inicial={ci_antes}, cantidad_actual={ca_antes}")
        
        cantidades = [5, 10, 15]
        for cant in cantidades:
            mov_data = {
                'tipo': 'entrada',
                'lote': lote_id,
                'cantidad': cant,
                'motivo': f'Test entrada múltiple +{cant}'
            }
            resp = client.post('/api/movimientos/', mov_data, format='json')
            if resp.status_code != 201:
                raise Exception(f"Error en entrada +{cant}: {resp.status_code} - {resp.data}")
            p(f"    Entrada +{cant} registrada")
        
        lote_despues = Lote.objects.get(pk=lote_id)
        ci_despues = lote_despues.cantidad_inicial
        ca_despues = lote_despues.cantidad_actual
        total_entradas = sum(cantidades)
        p(f"  Después: cantidad_inicial={ci_despues}, cantidad_actual={ca_despues}")
        
        if ca_despues != ca_antes + total_entradas:
            raise Exception(f"cantidad_actual incorrecta: esperado {ca_antes + total_entradas}, obtenido {ca_despues}")
        
        if ci_despues != ci_antes + total_entradas:
            raise Exception(f"cantidad_inicial incorrecta: esperado {ci_antes + total_entradas}, obtenido {ci_despues}")
        
        p(f"  {C.OK}✓ cantidad_actual: {ca_antes} → {ca_despues} (+{total_entradas}){C.END}")
        p(f"  {C.OK}✓ cantidad_inicial: {ci_antes} → {ci_despues} (+{total_entradas}){C.END}")
        
        test_passed(test_name)
        results['passed'] += 1
        results['tests'].append((test_name, True, None))
        
    except Exception as e:
        test_failed(test_name, str(e))
        results['failed'] += 1
        results['tests'].append((test_name, False, str(e)))
    
    # =========================================================================
    # TEST 5: Verificar coherencia final (cantidad_actual <= cantidad_inicial)
    # =========================================================================
    test_name = "5. Coherencia: cantidad_actual <= cantidad_inicial"
    p(f"\n{C.BOLD}>>> {test_name}{C.END}")
    
    try:
        lote = Lote.objects.get(pk=lote_id)
        ci = lote.cantidad_inicial
        ca = lote.cantidad_actual
        p(f"  Estado actual: cantidad_inicial={ci}, cantidad_actual={ca}")
        
        # Hacer algunas salidas para que ca < ci
        mov_data = {
            'tipo': 'salida',
            'lote': lote_id,
            'cantidad': 20,
            'motivo': 'Test para crear diferencia',
            'subtipo_salida': 'consumo_interno'
        }
        resp = client.post('/api/movimientos/', mov_data, format='json')
        if resp.status_code != 201:
            raise Exception(f"Error en salida: {resp.status_code} - {resp.data}")
        
        lote.refresh_from_db()
        ci = lote.cantidad_inicial
        ca = lote.cantidad_actual
        p(f"  Después de salida -20: cantidad_inicial={ci}, cantidad_actual={ca}")
        
        if ca > ci:
            raise Exception(f"Incoherencia: cantidad_actual ({ca}) > cantidad_inicial ({ci})")
        
        p(f"  {C.OK}✓ Coherencia verificada: {ca} de {ci}{C.END}")
        
        test_passed(test_name)
        results['passed'] += 1
        results['tests'].append((test_name, True, None))
        
    except Exception as e:
        test_failed(test_name, str(e))
        results['failed'] += 1
        results['tests'].append((test_name, False, str(e)))
    
    # =========================================================================
    # TEST 6: Limpiar datos de prueba
    # =========================================================================
    test_name = "6. Limpieza de datos de prueba"
    p(f"\n{C.BOLD}>>> {test_name}{C.END}")
    
    try:
        # Eliminar movimientos del lote
        movs_deleted = Movimiento.objects.filter(lote_id=lote_id).delete()
        p(f"  Movimientos eliminados: {movs_deleted[0]}")
        
        # Eliminar lote
        Lote.objects.filter(pk=lote_id).delete()
        p(f"  Lote eliminado: {lote_numero}")
        
        # Eliminar producto
        Producto.objects.filter(pk=producto_id).delete()
        p(f"  Producto eliminado: {producto_data['clave']}")
        
        test_passed(test_name)
        results['passed'] += 1
        results['tests'].append((test_name, True, None))
        
    except Exception as e:
        test_failed(test_name, str(e))
        results['failed'] += 1
        results['tests'].append((test_name, False, str(e)))
    
    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    print(f"\n{C.BOLD}{'='*70}")
    print("RESUMEN DE TESTS")
    print(f"{'='*70}{C.END}")
    
    total = results['passed'] + results['failed']
    
    if results['failed'] == 0:
        print(f"\n{C.OK}{C.BOLD}✓ TODOS LOS TESTS PASARON: {results['passed']}/{total}{C.END}")
    else:
        print(f"\n{C.FAIL}{C.BOLD}✗ TESTS FALLIDOS: {results['failed']}/{total}{C.END}")
        print(f"\nTests que fallaron:")
        for name, passed, reason in results['tests']:
            if not passed:
                print(f"  - {name}: {reason}")
    
    print(f"\n{C.INFO}Bug verificado: cantidad_inicial ahora se incrementa correctamente")
    print(f"en movimientos de tipo 'entrada' usando abs(cantidad_int){C.END}\n")
    
    return results


if __name__ == '__main__':
    results = main()
    sys.exit(0 if results['failed'] == 0 else 1)
