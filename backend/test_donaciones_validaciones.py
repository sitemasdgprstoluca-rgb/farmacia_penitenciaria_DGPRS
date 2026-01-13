"""
Test masivo de validaciones del módulo de donaciones.
Verifica todas las reglas de negocio para donaciones.
"""
import os
import sys

# Setup path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from django.utils import timezone
from core.models import Donacion, DetalleDonacion, ProductoDonacion, Centro, User
from core.views import DonacionViewSet
from core.serializers import DonacionSerializer

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

resultados = []

def registrar_test(nombre, paso, detalle=''):
    """Registrar resultado de un test."""
    icon = f"{Colors.GREEN}✓{Colors.END}" if paso else f"{Colors.RED}✗{Colors.END}"
    status = 'PASS' if paso else 'FAIL'
    resultados.append({'nombre': nombre, 'paso': paso, 'detalle': detalle})
    print(f"  {icon} {nombre}: {Colors.BOLD}{status}{Colors.END} {detalle if detalle else ''}")


def setup_data():
    """Crear datos de prueba."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}CONFIGURACIÓN DE DATOS DE PRUEBA{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    # Buscar o crear centro
    centro = Centro.objects.first()
    if not centro:
        centro = Centro.objects.create(
            nombre='Centro Test Donaciones',
            activo=True
        )
    print(f"  Centro: {centro.nombre} (ID: {centro.id})")
    
    # Buscar o crear admin
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        admin = User.objects.create_superuser(
            username='admin_test_don',
            email='admin@test.com',
            password='test1234',
            rol='admin'
        )
    print(f"  Admin: {admin.username} (ID: {admin.id})")
    
    # Buscar o crear producto de donación
    producto = ProductoDonacion.objects.filter(activo=True).first()
    if not producto:
        producto = ProductoDonacion.objects.create(
            clave='PDON-TEST-001',
            nombre='Producto Test Donación',
            unidad_medida='PIEZA',
            activo=True
        )
    print(f"  Producto: {producto.clave} - {producto.nombre}")
    
    return centro, admin, producto


def cleanup_test_data():
    """Limpiar donaciones de prueba."""
    Donacion.objects.filter(numero__startswith='TEST-').delete()
    print(f"  {Colors.YELLOW}Datos de prueba limpiados{Colors.END}")


def test_crear_donacion_sin_productos():
    """TEST 1: No debe permitir crear donación sin productos."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TEST 1: CREAR DONACIÓN SIN PRODUCTOS{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    centro, admin, producto = setup_data()
    factory = APIRequestFactory()
    
    # Intentar crear sin detalles
    data = {
        'donante_nombre': 'Test Sin Productos',
        'fecha_donacion': timezone.now().date().isoformat(),
        'centro_destino': centro.id,
        'detalles': []  # Sin productos
    }
    
    view = DonacionViewSet.as_view({'post': 'create'})
    request = factory.post('/api/donaciones/', data, format='json')
    force_authenticate(request, user=admin)
    response = view(request)
    
    # Debe fallar con 400
    if response.status_code == 400:
        error_msg = str(response.data)
        registrar_test('Rechaza donación sin productos en CREATE', True, 
                      f'Status: {response.status_code}')
    else:
        registrar_test('Rechaza donación sin productos en CREATE', False,
                      f'Status inesperado: {response.status_code}')


def test_crear_donacion_con_productos():
    """TEST 2: Debe permitir crear donación CON productos."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TEST 2: CREAR DONACIÓN CON PRODUCTOS{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    centro, admin, producto = setup_data()
    factory = APIRequestFactory()
    
    import random
    numero_test = f"TEST-{random.randint(10000, 99999)}"
    
    data = {
        'numero': numero_test,
        'donante_nombre': 'Donante Test Completo',
        'donante_tipo': 'empresa',
        'fecha_donacion': timezone.now().date().isoformat(),
        'centro_destino': centro.id,
        'detalles': [
            {
                'producto_donacion': producto.id,
                'cantidad': 100,
                'numero_lote': 'LOTE-TEST-001',
                'estado_producto': 'bueno'
            }
        ]
    }
    
    view = DonacionViewSet.as_view({'post': 'create'})
    request = factory.post('/api/donaciones/', data, format='json')
    force_authenticate(request, user=admin)
    response = view(request)
    
    if response.status_code == 201:
        donacion_id = response.data.get('id')
        registrar_test('Permite crear donación con productos', True,
                      f'Donación ID: {donacion_id}')
        return donacion_id
    else:
        registrar_test('Permite crear donación con productos', False,
                      f'Error: {response.data}')
        return None


def test_recibir_donacion_sin_productos():
    """TEST 3: No debe permitir recibir donación sin productos."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TEST 3: RECIBIR DONACIÓN SIN PRODUCTOS{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    centro, admin, producto = setup_data()
    factory = APIRequestFactory()
    
    # Crear donación directamente en BD sin detalles (simulando bug anterior)
    import random
    numero_test = f"TEST-VACIA-{random.randint(10000, 99999)}"
    
    donacion = Donacion.objects.create(
        numero=numero_test,
        donante_nombre='Donación Vacía Test',
        fecha_donacion=timezone.now().date(),
        centro_destino=centro,
        estado='pendiente'
    )
    
    # Intentar recibir
    view = DonacionViewSet.as_view({'post': 'recibir'})
    request = factory.post(f'/api/donaciones/{donacion.id}/recibir/')
    force_authenticate(request, user=admin)
    response = view(request, pk=donacion.id)
    
    if response.status_code == 400:
        registrar_test('Rechaza RECIBIR donación sin productos', True,
                      f'Status: {response.status_code}')
    else:
        registrar_test('Rechaza RECIBIR donación sin productos', False,
                      f'Status inesperado: {response.status_code}, Data: {response.data}')
    
    # Limpiar
    donacion.delete()


def test_procesar_donacion_sin_productos():
    """TEST 4: No debe permitir procesar donación sin productos."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TEST 4: PROCESAR DONACIÓN SIN PRODUCTOS{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    centro, admin, producto = setup_data()
    factory = APIRequestFactory()
    
    # Crear donación directamente en BD sin detalles
    import random
    numero_test = f"TEST-PROC-{random.randint(10000, 99999)}"
    
    donacion = Donacion.objects.create(
        numero=numero_test,
        donante_nombre='Donación Vacía Para Procesar',
        fecha_donacion=timezone.now().date(),
        centro_destino=centro,
        estado='recibida'  # Estado que permite procesar
    )
    
    # Intentar procesar
    view = DonacionViewSet.as_view({'post': 'procesar'})
    request = factory.post(f'/api/donaciones/{donacion.id}/procesar/')
    force_authenticate(request, user=admin)
    response = view(request, pk=donacion.id)
    
    if response.status_code == 400:
        registrar_test('Rechaza PROCESAR donación sin productos', True,
                      f'Status: {response.status_code}')
    else:
        registrar_test('Rechaza PROCESAR donación sin productos', False,
                      f'Status inesperado: {response.status_code}, Data: {response.data}')
    
    # Limpiar
    donacion.delete()


def test_procesar_donacion_con_productos():
    """TEST 5: Debe permitir procesar donación CON productos."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TEST 5: PROCESAR DONACIÓN CON PRODUCTOS{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    centro, admin, producto = setup_data()
    factory = APIRequestFactory()
    
    # Crear donación con detalle
    import random
    numero_test = f"TEST-PROC-OK-{random.randint(10000, 99999)}"
    
    donacion = Donacion.objects.create(
        numero=numero_test,
        donante_nombre='Donación Para Procesar OK',
        fecha_donacion=timezone.now().date(),
        centro_destino=centro,
        estado='recibida'
    )
    
    # Agregar detalle
    detalle = DetalleDonacion.objects.create(
        donacion=donacion,
        producto_donacion=producto,
        cantidad=50,
        cantidad_disponible=0,
        numero_lote='LOTE-PROC-001',
        estado_producto='bueno'
    )
    
    # Procesar
    view = DonacionViewSet.as_view({'post': 'procesar'})
    request = factory.post(f'/api/donaciones/{donacion.id}/procesar/')
    force_authenticate(request, user=admin)
    response = view(request, pk=donacion.id)
    
    if response.status_code == 200:
        # Verificar que el estado cambió
        donacion.refresh_from_db()
        detalle.refresh_from_db()
        
        registrar_test('Permite PROCESAR donación con productos', True,
                      f'Estado: {donacion.estado}')
        registrar_test('Stock disponible actualizado', detalle.cantidad_disponible == 50,
                      f'Disponible: {detalle.cantidad_disponible}')
    else:
        registrar_test('Permite PROCESAR donación con productos', False,
                      f'Error: {response.data}')
    
    # Limpiar
    donacion.delete()


def test_update_donacion_quitando_productos():
    """TEST 6: No debe permitir actualizar dejando sin productos."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TEST 6: UPDATE QUITANDO TODOS LOS PRODUCTOS{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    centro, admin, producto = setup_data()
    factory = APIRequestFactory()
    
    # Crear donación con detalle
    import random
    numero_test = f"TEST-UPD-{random.randint(10000, 99999)}"
    
    donacion = Donacion.objects.create(
        numero=numero_test,
        donante_nombre='Donación Para Update',
        fecha_donacion=timezone.now().date(),
        centro_destino=centro,
        estado='pendiente'
    )
    
    DetalleDonacion.objects.create(
        donacion=donacion,
        producto_donacion=producto,
        cantidad=30,
        cantidad_disponible=0,
        estado_producto='bueno'
    )
    
    # Intentar actualizar con detalles vacíos
    data = {
        'donante_nombre': 'Nuevo Nombre',
        'fecha_donacion': timezone.now().date().isoformat(),
        'detalles': []  # Quitando todos los productos
    }
    
    view = DonacionViewSet.as_view({'put': 'update'})
    request = factory.put(f'/api/donaciones/{donacion.id}/', data, format='json')
    force_authenticate(request, user=admin)
    response = view(request, pk=donacion.id)
    
    if response.status_code == 400:
        registrar_test('Rechaza UPDATE quitando todos los productos', True,
                      f'Status: {response.status_code}')
    else:
        registrar_test('Rechaza UPDATE quitando todos los productos', False,
                      f'Status inesperado: {response.status_code}')
    
    # Limpiar
    donacion.delete()


def test_flujo_completo():
    """TEST 7: Flujo completo de donación válida."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TEST 7: FLUJO COMPLETO DONACIÓN{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    centro, admin, producto = setup_data()
    factory = APIRequestFactory()
    
    import random
    numero_test = f"TEST-FLUJO-{random.randint(10000, 99999)}"
    
    # 1. Crear donación
    data = {
        'numero': numero_test,
        'donante_nombre': 'Donante Flujo Completo',
        'donante_tipo': 'ong',
        'fecha_donacion': timezone.now().date().isoformat(),
        'centro_destino': centro.id,
        'detalles': [
            {
                'producto_donacion': producto.id,
                'cantidad': 200,
                'numero_lote': 'LOTE-FLUJO-001',
                'estado_producto': 'bueno'
            },
            {
                'producto_donacion': producto.id,
                'cantidad': 150,
                'numero_lote': 'LOTE-FLUJO-002',
                'fecha_caducidad': '2027-12-31',
                'estado_producto': 'bueno'
            }
        ]
    }
    
    view = DonacionViewSet.as_view({'post': 'create'})
    request = factory.post('/api/donaciones/', data, format='json')
    force_authenticate(request, user=admin)
    response = view(request)
    
    if response.status_code != 201:
        registrar_test('Crear donación con múltiples productos', False,
                      f'Error: {response.data}')
        return
    
    donacion_id = response.data['id']
    registrar_test('Crear donación con múltiples productos', True,
                  f'ID: {donacion_id}, Detalles: {len(response.data.get("detalles", []))}')
    
    # 2. Recibir donación
    view = DonacionViewSet.as_view({'post': 'recibir'})
    request = factory.post(f'/api/donaciones/{donacion_id}/recibir/')
    force_authenticate(request, user=admin)
    response = view(request, pk=donacion_id)
    
    if response.status_code == 200:
        registrar_test('Recibir donación', True, f'Estado: {response.data.get("estado")}')
    else:
        registrar_test('Recibir donación', False, f'Error: {response.data}')
        return
    
    # 3. Procesar donación
    view = DonacionViewSet.as_view({'post': 'procesar'})
    request = factory.post(f'/api/donaciones/{donacion_id}/procesar/')
    force_authenticate(request, user=admin)
    response = view(request, pk=donacion_id)
    
    if response.status_code == 200:
        donacion_data = response.data.get('donacion', {})
        registrar_test('Procesar donación', True, f'Estado: {donacion_data.get("estado")}')
        
        # Verificar stock disponible
        donacion = Donacion.objects.get(pk=donacion_id)
        total_disponible = sum(d.cantidad_disponible for d in donacion.detalles.all())
        registrar_test('Stock total disponible correcto', total_disponible == 350,
                      f'Total: {total_disponible} (esperado: 350)')
    else:
        registrar_test('Procesar donación', False, f'Error: {response.data}')
    
    # Limpiar
    Donacion.objects.filter(pk=donacion_id).delete()


def test_procesar_todas():
    """TEST 8: Procesar todas las donaciones pendientes."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TEST 8: PROCESAR TODAS LAS DONACIONES{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    centro, admin, producto = setup_data()
    factory = APIRequestFactory()
    
    import random
    
    # Crear 2 donaciones con productos y 1 sin productos
    donaciones_ids = []
    
    # Donación 1: con productos
    don1 = Donacion.objects.create(
        numero=f"TEST-TODAS-1-{random.randint(1000, 9999)}",
        donante_nombre='Donación Múltiple 1',
        fecha_donacion=timezone.now().date(),
        centro_destino=centro,
        estado='pendiente'
    )
    DetalleDonacion.objects.create(
        donacion=don1,
        producto_donacion=producto,
        cantidad=10,
        cantidad_disponible=0,
        estado_producto='bueno'
    )
    donaciones_ids.append(don1.id)
    
    # Donación 2: con productos
    don2 = Donacion.objects.create(
        numero=f"TEST-TODAS-2-{random.randint(1000, 9999)}",
        donante_nombre='Donación Múltiple 2',
        fecha_donacion=timezone.now().date(),
        centro_destino=centro,
        estado='recibida'
    )
    DetalleDonacion.objects.create(
        donacion=don2,
        producto_donacion=producto,
        cantidad=20,
        cantidad_disponible=0,
        estado_producto='bueno'
    )
    donaciones_ids.append(don2.id)
    
    # Donación 3: SIN productos (debe ser ignorada)
    don3 = Donacion.objects.create(
        numero=f"TEST-TODAS-3-{random.randint(1000, 9999)}",
        donante_nombre='Donación Vacía',
        fecha_donacion=timezone.now().date(),
        centro_destino=centro,
        estado='pendiente'
    )
    donaciones_ids.append(don3.id)
    
    # Procesar todas
    view = DonacionViewSet.as_view({'post': 'procesar_todas'})
    request = factory.post('/api/donaciones/procesar-todas/')
    force_authenticate(request, user=admin)
    response = view(request)
    
    if response.status_code == 200:
        procesadas = response.data.get('procesadas', 0)
        errores = response.data.get('errores', [])
        
        registrar_test('Procesar todas ejecutado', True, 
                      f'Procesadas: {procesadas}, Errores: {len(errores)}')
        registrar_test('Solo procesa donaciones con productos', procesadas == 2,
                      f'Procesadas: {procesadas} (esperado: 2)')
        registrar_test('Reporta donaciones sin productos', len(errores) >= 1,
                      f'Errores reportados: {len(errores)}')
    else:
        registrar_test('Procesar todas', False, f'Error: {response.data}')
    
    # Limpiar
    Donacion.objects.filter(id__in=donaciones_ids).delete()


def imprimir_resumen():
    """Imprimir resumen de tests."""
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}RESUMEN DE TESTS - VALIDACIONES DONACIONES{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    total = len(resultados)
    pasados = sum(1 for r in resultados if r['paso'])
    fallidos = total - pasados
    
    for r in resultados:
        icon = f"{Colors.GREEN}✓{Colors.END}" if r['paso'] else f"{Colors.RED}✗{Colors.END}"
        print(f"  {icon} {r['nombre']}")
    
    print(f"\n{Colors.BLUE}{'-'*70}{Colors.END}")
    print(f"  {Colors.BOLD}Total:{Colors.END} {total} tests")
    print(f"  {Colors.GREEN}Pasados:{Colors.END} {pasados}")
    print(f"  {Colors.RED}Fallidos:{Colors.END} {fallidos}")
    
    porcentaje = (pasados / total * 100) if total > 0 else 0
    color = Colors.GREEN if porcentaje >= 80 else Colors.YELLOW if porcentaje >= 50 else Colors.RED
    print(f"  {Colors.BOLD}Porcentaje:{Colors.END} {color}{porcentaje:.1f}%{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}\n")
    
    return fallidos == 0


if __name__ == '__main__':
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║     TEST MASIVO - VALIDACIONES MÓDULO DONACIONES                     ║")
    print("║     Sistema de Inventario Farmacéutico Penitenciario                 ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    try:
        # Ejecutar tests
        test_crear_donacion_sin_productos()
        test_crear_donacion_con_productos()
        test_recibir_donacion_sin_productos()
        test_procesar_donacion_sin_productos()
        test_procesar_donacion_con_productos()
        test_update_donacion_quitando_productos()
        test_flujo_completo()
        test_procesar_todas()
        
        # Limpiar datos de prueba
        cleanup_test_data()
        
        # Resumen
        exito = imprimir_resumen()
        
        sys.exit(0 if exito else 1)
        
    except Exception as e:
        print(f"\n{Colors.RED}ERROR CRÍTICO: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
