#!/usr/bin/env python
"""
Pruebas de API - Flujo Multinivel Compras de Caja Chica
========================================================
Ejecuta pruebas reales contra la API del backend.

REQUISITOS:
- El servidor de backend debe estar corriendo en localhost:8000
- Debe existir un usuario de prueba o superuser

Ejecutar: python test_api_caja_chica.py
"""
import os
import sys
import json
import requests
from datetime import date, timedelta

# Configuración
BASE_URL = os.getenv('API_URL', 'http://localhost:8000/api')
TOKEN = None

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")

def print_success(text):
    print(f"  {Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"  {Colors.RED}✗ {text}{Colors.RESET}")

def print_info(text):
    print(f"  {Colors.BLUE}ℹ {text}{Colors.RESET}")

def print_warning(text):
    print(f"  {Colors.YELLOW}⚠ {text}{Colors.RESET}")


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
    
    def add_pass(self, test):
        self.passed += 1
        print_success(test)
    
    def add_fail(self, test, error=""):
        self.failed += 1
        self.errors.append((test, error))
        print_error(f"{test}" + (f": {error}" if error else ""))
    
    def add_skip(self, test):
        self.skipped += 1
        print_warning(f"SKIP: {test}")
    
    def summary(self):
        print_header("RESUMEN")
        total = self.passed + self.failed
        print(f"  Total: {total}")
        print(f"  {Colors.GREEN}Pasadas: {self.passed}{Colors.RESET}")
        print(f"  {Colors.RED}Fallidas: {self.failed}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Omitidas: {self.skipped}{Colors.RESET}")
        return self.failed == 0


results = TestResults()


def get_auth_token():
    """Obtiene token de autenticación"""
    global TOKEN
    
    # Intentar con credenciales por defecto
    credentials = [
        ('admin', 'admin123'),
        ('devusa', 'devusapassword'),
        ('farmacia', 'farmacia123'),
    ]
    
    for username, password in credentials:
        try:
            response = requests.post(f'{BASE_URL}/token/', json={
                'username': username,
                'password': password
            }, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                TOKEN = data.get('access')
                print_success(f"Autenticado como: {username}")
                return TOKEN
        except Exception as e:
            continue
    
    print_error("No se pudo autenticar con ninguna credencial")
    return None


def api_get(endpoint):
    """GET request con autenticación"""
    headers = {}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    
    try:
        response = requests.get(f'{BASE_URL}{endpoint}', headers=headers, timeout=10)
        return response
    except Exception as e:
        return None


def api_post(endpoint, data=None):
    """POST request con autenticación"""
    headers = {'Content-Type': 'application/json'}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    
    try:
        response = requests.post(f'{BASE_URL}{endpoint}', 
                                json=data or {}, 
                                headers=headers, 
                                timeout=10)
        return response
    except Exception as e:
        return None


def check_server():
    """Verifica que el servidor está corriendo"""
    print_header("VERIFICANDO SERVIDOR")
    
    try:
        response = requests.get(f'{BASE_URL}/', timeout=5)
        print_success(f"Servidor respondiendo en {BASE_URL}")
        return True
    except requests.exceptions.ConnectionError:
        print_error(f"No se puede conectar a {BASE_URL}")
        print_info("Asegúrate de que el servidor Django está corriendo:")
        print_info("  cd backend && python manage.py runserver")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False


def test_list_endpoint():
    """Prueba el endpoint de listar compras"""
    print_header("1. ENDPOINT: LISTAR COMPRAS")
    
    response = api_get('/compras-caja-chica/')
    
    if not response:
        results.add_fail("GET /compras-caja-chica/", "Sin respuesta")
        return
    
    if response.status_code == 200:
        data = response.json()
        results.add_pass(f"GET /compras-caja-chica/ - Status: 200")
        
        # Verificar estructura de respuesta
        if isinstance(data, dict) and 'results' in data:
            results.add_pass(f"Respuesta paginada con {len(data['results'])} compras")
        elif isinstance(data, list):
            results.add_pass(f"Respuesta lista con {len(data)} compras")
        else:
            results.add_fail("Estructura de respuesta", "Formato inesperado")
    else:
        results.add_fail(f"GET /compras-caja-chica/", f"Status: {response.status_code}")


def test_resumen_endpoint():
    """Prueba el endpoint de resumen"""
    print_header("2. ENDPOINT: RESUMEN")
    
    response = api_get('/compras-caja-chica/resumen/')
    
    if not response:
        results.add_fail("GET /compras-caja-chica/resumen/", "Sin respuesta")
        return
    
    if response.status_code == 200:
        data = response.json()
        results.add_pass(f"GET /compras-caja-chica/resumen/ - Status: 200")
        
        # Verificar campos del resumen
        expected_fields = ['total_compras', 'por_estado', 'total_gastado']
        for field in expected_fields:
            if field in data:
                results.add_pass(f"Campo '{field}' presente en resumen")
            else:
                results.add_fail(f"Campo '{field}' en resumen", "No encontrado")
    else:
        results.add_fail(f"GET /compras-caja-chica/resumen/", f"Status: {response.status_code}")


def test_crear_compra():
    """Prueba crear una compra"""
    print_header("3. ENDPOINT: CREAR COMPRA")
    
    # Primero obtener un centro
    centros_response = api_get('/centros/')
    centro_id = None
    
    if centros_response and centros_response.status_code == 200:
        centros = centros_response.json()
        if isinstance(centros, dict) and 'results' in centros:
            centros = centros['results']
        if centros:
            centro_id = centros[0]['id']
            print_info(f"Usando centro ID: {centro_id}")
    
    if not centro_id:
        results.add_skip("POST /compras-caja-chica/ - Sin centro disponible")
        return None
    
    # Crear compra
    data = {
        'centro': centro_id,
        'motivo_compra': 'Prueba automatizada de API - Flujo multinivel',
        'proveedor_nombre': 'Farmacia de Prueba',
        'detalles': [
            {
                'descripcion_producto': 'Paracetamol 500mg - Test',
                'cantidad_solicitada': 10,
                'precio_unitario': '25.00'
            }
        ]
    }
    
    response = api_post('/compras-caja-chica/', data)
    
    if not response:
        results.add_fail("POST /compras-caja-chica/", "Sin respuesta")
        return None
    
    if response.status_code in [200, 201]:
        compra = response.json()
        results.add_pass(f"POST /compras-caja-chica/ - Status: {response.status_code}")
        results.add_pass(f"Compra creada con ID: {compra.get('id')}")
        results.add_pass(f"Estado inicial: {compra.get('estado')}")
        return compra.get('id')
    else:
        error_detail = response.json() if response.content else 'Sin detalles'
        results.add_fail(f"POST /compras-caja-chica/", f"Status: {response.status_code} - {error_detail}")
        return None


def test_flujo_compra(compra_id):
    """Prueba el flujo completo de una compra"""
    print_header("4. PRUEBA DE FLUJO MULTINIVEL")
    
    if not compra_id:
        results.add_skip("Flujo multinivel - Sin compra de prueba")
        return
    
    # 4.1 Enviar a Admin
    print_info("Probando: pendiente -> enviada_admin")
    response = api_post(f'/compras-caja-chica/{compra_id}/enviar-admin/')
    
    if response and response.status_code == 200:
        results.add_pass("Transición: pendiente -> enviada_admin")
    else:
        status = response.status_code if response else 'Sin respuesta'
        detail = response.json() if response and response.content else ''
        results.add_fail(f"Transición: pendiente -> enviada_admin", f"Status: {status}")
        return
    
    # 4.2 Autorizar Admin
    print_info("Probando: enviada_admin -> autorizada_admin")
    response = api_post(f'/compras-caja-chica/{compra_id}/autorizar-admin/')
    
    if response and response.status_code == 200:
        results.add_pass("Transición: enviada_admin -> autorizada_admin")
    else:
        results.add_fail("Transición: enviada_admin -> autorizada_admin")
        return
    
    # 4.3 Enviar a Director
    print_info("Probando: autorizada_admin -> enviada_director")
    response = api_post(f'/compras-caja-chica/{compra_id}/enviar-director/')
    
    if response and response.status_code == 200:
        results.add_pass("Transición: autorizada_admin -> enviada_director")
    else:
        results.add_fail("Transición: autorizada_admin -> enviada_director")
        return
    
    # 4.4 Autorizar Director
    print_info("Probando: enviada_director -> autorizada")
    response = api_post(f'/compras-caja-chica/{compra_id}/autorizar-director/')
    
    if response and response.status_code == 200:
        data = response.json()
        results.add_pass("Transición: enviada_director -> autorizada")
        results.add_pass(f"Estado final: {data.get('estado')}")
        
        # Verificar que tiene los campos del flujo
        if data.get('fecha_envio_admin'):
            results.add_pass("Campo fecha_envio_admin poblado")
        if data.get('fecha_autorizacion_admin'):
            results.add_pass("Campo fecha_autorizacion_admin poblado")
        if data.get('fecha_autorizacion_director'):
            results.add_pass("Campo fecha_autorizacion_director poblado")
    else:
        results.add_fail("Transición: enviada_director -> autorizada")


def test_acciones_disponibles():
    """Verifica que acciones_disponibles funciona correctamente"""
    print_header("5. VERIFICAR ACCIONES DISPONIBLES")
    
    # Obtener una compra
    response = api_get('/compras-caja-chica/')
    
    if not response or response.status_code != 200:
        results.add_skip("Acciones disponibles - Sin compras")
        return
    
    data = response.json()
    compras = data.get('results', []) if isinstance(data, dict) else data
    
    if compras:
        compra = compras[0]
        
        # Obtener detalle de la compra
        detail_response = api_get(f"/compras-caja-chica/{compra['id']}/")
        
        if detail_response and detail_response.status_code == 200:
            detail = detail_response.json()
            
            if 'acciones_disponibles' in detail:
                acciones = detail['acciones_disponibles']
                results.add_pass(f"Campo 'acciones_disponibles' presente")
                results.add_pass(f"Acciones para estado '{detail.get('estado')}': {acciones}")
            else:
                results.add_fail("Campo 'acciones_disponibles' no encontrado")
        else:
            results.add_fail("GET /compras-caja-chica/{id}/")
    else:
        results.add_skip("Acciones disponibles - Sin compras para verificar")


def cleanup_test_data(compra_id):
    """Limpia datos de prueba"""
    print_header("6. LIMPIEZA")
    
    if not compra_id:
        print_info("Sin datos de prueba para limpiar")
        return
    
    # Intentar cancelar la compra de prueba
    response = api_post(f'/compras-caja-chica/{compra_id}/cancelar/', {
        'motivo_cancelacion': 'Limpieza de prueba automatizada'
    })
    
    if response and response.status_code == 200:
        results.add_pass(f"Compra {compra_id} cancelada (limpieza)")
    else:
        print_warning(f"No se pudo cancelar compra {compra_id} (puede estar en estado no cancelable)")


def main():
    print(f"\n{Colors.BOLD}{'*'*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  PRUEBAS DE API - FLUJO MULTINIVEL CAJA CHICA{Colors.RESET}")
    print(f"{Colors.BOLD}{'*'*60}{Colors.RESET}")
    
    # 1. Verificar servidor
    if not check_server():
        print_error("\n⚠️  El servidor no está disponible")
        print_info("Ejecuta: cd backend && python manage.py runserver")
        return 1
    
    # 2. Autenticar
    if not get_auth_token():
        print_error("\n⚠️  No se pudo autenticar")
        return 1
    
    # 3. Ejecutar pruebas
    test_list_endpoint()
    test_resumen_endpoint()
    compra_id = test_crear_compra()
    test_flujo_compra(compra_id)
    test_acciones_disponibles()
    cleanup_test_data(compra_id)
    
    # 4. Resumen
    success = results.summary()
    
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    if success:
        print(f"{Colors.GREEN}{Colors.BOLD}  ✓ TODAS LAS PRUEBAS DE API PASARON{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}  ✗ ALGUNAS PRUEBAS FALLARON{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
