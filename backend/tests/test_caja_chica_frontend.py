"""
Test de integración Frontend-Backend para Compras de Caja Chica
Verifica que los endpoints retornan datos en el formato esperado por el frontend
"""

import os
import sys
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import TestCase
from rest_framework.test import APIClient
from core.models import User, Centro, Producto


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_ok(msg):
    print(f"{Colors.GREEN}✓{Colors.ENDC} {msg}")

def print_fail(msg):
    print(f"{Colors.RED}✗{Colors.ENDC} {msg}")

def print_info(msg):
    print(f"{Colors.CYAN}ℹ{Colors.ENDC} {msg}")


def test_frontend_api_compatibility():
    """Verifica que la API retorna los campos esperados por el frontend"""
    
    print(f"\n{Colors.BOLD}{'='*60}")
    print("TEST DE COMPATIBILIDAD FRONTEND-BACKEND")
    print(f"{'='*60}{Colors.ENDC}\n")
    
    client = APIClient()
    
    # Autenticar
    user = User.objects.filter(is_superuser=True, is_active=True).first()
    if not user:
        user = User.objects.filter(is_active=True).first()
    
    if not user:
        print_fail("No hay usuarios disponibles")
        return
    
    client.force_authenticate(user=user)
    print_ok(f"Autenticado como: {user.username}")
    
    results = {'passed': 0, 'failed': 0}
    
    # 1. Test GET /api/compras-caja-chica/
    print_info("\n1. Test: GET /api/compras-caja-chica/")
    response = client.get('/api/compras-caja-chica/')
    
    if response.status_code == 200:
        print_ok(f"Status: {response.status_code}")
        data = response.data
        
        # Verificar estructura de respuesta
        expected_fields_list = ['count', 'next', 'previous', 'results']
        if all(f in data for f in expected_fields_list):
            print_ok("Paginación correcta (count, next, previous, results)")
            results['passed'] += 1
        else:
            print_fail("Estructura de paginación incorrecta")
            results['failed'] += 1
        
        # Si hay resultados, verificar campos de cada compra
        if data.get('results') and len(data['results']) > 0:
            compra = data['results'][0]
            expected_compra_fields = ['id', 'folio', 'estado', 'centro', 'motivo_compra', 'total']
            
            missing = [f for f in expected_compra_fields if f not in compra]
            if not missing:
                print_ok(f"Campos de compra correctos: {', '.join(expected_compra_fields)}")
                results['passed'] += 1
            else:
                print_fail(f"Campos faltantes en compra: {missing}")
                results['failed'] += 1
                print(f"  Campos recibidos: {list(compra.keys())}")
    else:
        print_fail(f"Error: {response.status_code}")
        results['failed'] += 1
    
    # 2. Test crear compra con datos del frontend
    print_info("\n2. Test: POST /api/compras-caja-chica/ (formato frontend)")
    
    centro = Centro.objects.filter(activo=True).first()
    producto = Producto.objects.filter(activo=True).first()
    
    if centro and producto:
        frontend_data = {
            'centro': centro.id,
            'motivo_compra': 'Test desde frontend',
            'proveedor_nombre': 'Farmacia San Pablo',
            'proveedor_rfc': 'FSP123456789',
            'proveedor_direccion': 'Calle Principal 123',
            'proveedor_telefono': '555-1234567',
            'observaciones': 'Compra de prueba',
            'detalles': [
                {
                    'producto': producto.id,
                    'descripcion_producto': producto.nombre,
                    'cantidad_solicitada': 10,
                    'precio_unitario': '150.00',
                    'unidad_medida': producto.unidad_medida or 'PIEZA'
                }
            ]
        }
        
        response = client.post(
            '/api/compras-caja-chica/',
            data=json.dumps(frontend_data),
            content_type='application/json'
        )
        
        if response.status_code in [200, 201]:
            print_ok(f"Compra creada exitosamente (ID: {response.data.get('id')})")
            
            # Verificar que retorna campos que el frontend necesita
            expected_response_fields = ['id', 'folio', 'estado']
            if all(f in response.data for f in expected_response_fields):
                print_ok(f"Respuesta incluye: {', '.join(expected_response_fields)}")
                results['passed'] += 1
            else:
                print_fail("Respuesta incompleta")
                results['failed'] += 1
        else:
            print_fail(f"Error creando compra: {response.status_code}")
            print(f"  Detalle: {response.data}")
            results['failed'] += 1
    else:
        print_fail("No hay centro o producto para prueba")
        results['failed'] += 1
    
    # 3. Test GET /api/inventario-caja-chica/
    print_info("\n3. Test: GET /api/inventario-caja-chica/")
    response = client.get('/api/inventario-caja-chica/')
    
    if response.status_code == 200:
        print_ok(f"Status: {response.status_code}")
        results['passed'] += 1
    else:
        print_fail(f"Error: {response.status_code}")
        results['failed'] += 1
    
    # 4. Test GET /api/movimientos-caja-chica/
    print_info("\n4. Test: GET /api/movimientos-caja-chica/")
    response = client.get('/api/movimientos-caja-chica/')
    
    if response.status_code == 200:
        print_ok(f"Status: {response.status_code}")
        results['passed'] += 1
    else:
        print_fail(f"Error: {response.status_code}")
        results['failed'] += 1
    
    # 5. Test filtros (que usa el frontend)
    print_info("\n5. Test: Filtros del frontend")
    
    # Filtro por estado
    response = client.get('/api/compras-caja-chica/?estado=pendiente')
    if response.status_code == 200:
        print_ok("Filtro por estado funciona")
        results['passed'] += 1
    else:
        print_fail("Filtro por estado falló")
        results['failed'] += 1
    
    # Filtro por centro
    if centro:
        response = client.get(f'/api/compras-caja-chica/?centro={centro.id}')
        if response.status_code == 200:
            print_ok("Filtro por centro funciona")
            results['passed'] += 1
        else:
            print_fail("Filtro por centro falló")
            results['failed'] += 1
    
    # Búsqueda
    response = client.get('/api/compras-caja-chica/?search=test')
    if response.status_code == 200:
        print_ok("Búsqueda funciona")
        results['passed'] += 1
    else:
        print_fail("Búsqueda falló")
        results['failed'] += 1
    
    # Resumen
    print(f"\n{Colors.BOLD}{'='*60}")
    print("RESUMEN")
    print(f"{'='*60}{Colors.ENDC}")
    print(f"Pruebas pasadas: {Colors.GREEN}{results['passed']}{Colors.ENDC}")
    print(f"Pruebas fallidas: {Colors.RED}{results['failed']}{Colors.ENDC}")
    
    if results['failed'] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ API compatible con frontend{Colors.ENDC}")
    else:
        print(f"\n{Colors.YELLOW}⚠ Revisar compatibilidad{Colors.ENDC}")


def test_workflow_actions():
    """Prueba las acciones del workflow que usa el frontend"""
    
    print(f"\n{Colors.BOLD}{'='*60}")
    print("TEST DE ACCIONES DE WORKFLOW")
    print(f"{'='*60}{Colors.ENDC}\n")
    
    client = APIClient()
    
    user = User.objects.filter(is_superuser=True, is_active=True).first()
    if not user:
        user = User.objects.filter(is_active=True).first()
    
    client.force_authenticate(user=user)
    
    centro = Centro.objects.filter(activo=True).first()
    producto = Producto.objects.filter(activo=True).first()
    
    results = {'passed': 0, 'failed': 0}
    
    # Crear compra para prueba
    compra_data = {
        'centro': centro.id,
        'motivo_compra': 'Test workflow',
        'proveedor_nombre': 'Proveedor Test',
        'detalles': [{
            'producto': producto.id,
            'descripcion_producto': producto.nombre,
            'cantidad_solicitada': 5,
            'precio_unitario': '100.00'
        }]
    }
    
    response = client.post(
        '/api/compras-caja-chica/',
        data=json.dumps(compra_data),
        content_type='application/json'
    )
    
    if response.status_code not in [200, 201]:
        print_fail("No se pudo crear compra para prueba")
        return
    
    compra_id = response.data['id']
    print_ok(f"Compra creada: ID {compra_id}")
    
    # 1. Autorizar
    print_info("\n1. Acción: autorizar")
    response = client.post(
        f'/api/compras-caja-chica/{compra_id}/autorizar/',
        data=json.dumps({'observaciones': 'Autorizado para prueba'}),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        print_ok(f"Autorizar OK - Estado: {response.data.get('estado')}")
        results['passed'] += 1
    else:
        print_fail(f"Autorizar falló: {response.data}")
        results['failed'] += 1
    
    # 2. Registrar compra
    print_info("\n2. Acción: registrar_compra")
    response = client.post(
        f'/api/compras-caja-chica/{compra_id}/registrar_compra/',
        data=json.dumps({
            'numero_factura': 'FACT-TEST-001',
            'fecha_compra': '2026-01-13'
        }),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        print_ok(f"Registrar compra OK - Estado: {response.data.get('estado')}")
        results['passed'] += 1
    else:
        print_fail(f"Registrar compra falló: {response.data}")
        results['failed'] += 1
    
    # 3. Recibir
    print_info("\n3. Acción: recibir")
    response = client.post(
        f'/api/compras-caja-chica/{compra_id}/recibir/',
        data=json.dumps({'observaciones': 'Recibido correctamente'}),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        print_ok(f"Recibir OK - Estado: {response.data.get('estado')}")
        results['passed'] += 1
    else:
        print_fail(f"Recibir falló: {response.data}")
        results['failed'] += 1
    
    # 4. Verificar estado final
    print_info("\n4. Verificar estado final")
    response = client.get(f'/api/compras-caja-chica/{compra_id}/')
    
    if response.status_code == 200:
        estado = response.data.get('estado')
        if estado == 'recibida':
            print_ok(f"Estado final correcto: {estado}")
            results['passed'] += 1
        else:
            print_fail(f"Estado incorrecto: {estado} (esperado: recibida)")
            results['failed'] += 1
    
    # Resumen
    print(f"\n{Colors.BOLD}{'='*60}")
    print("RESUMEN WORKFLOW")
    print(f"{'='*60}{Colors.ENDC}")
    print(f"Pasadas: {Colors.GREEN}{results['passed']}{Colors.ENDC}")
    print(f"Fallidas: {Colors.RED}{results['failed']}{Colors.ENDC}")


if __name__ == '__main__':
    test_frontend_api_compatibility()
    test_workflow_actions()
    
    print(f"\n{Colors.BOLD}{'='*60}")
    print("PRUEBAS DE INTEGRACIÓN COMPLETADAS")
    print(f"{'='*60}{Colors.ENDC}\n")
