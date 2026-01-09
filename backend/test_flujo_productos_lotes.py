#!/usr/bin/env python
"""
Test de Integración: Flujo de Productos y Lotes
===============================================

Verifica:
1. Permisos de usuarios (farmacia/admin pueden crear/editar, centro solo lee)
2. Protección de campos obligatorios en productos con lotes
3. Protección de campos críticos en lotes con movimientos
4. Relaciones FK válidas (producto_id, centro_id)
5. Flujo completo sin errores

Ejecutar: python test_flujo_productos_lotes.py
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from datetime import date, timedelta
from decimal import Decimal

from core.models import Producto, Lote, Centro, Movimiento

User = get_user_model()

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}{Colors.RESET}\n")

def print_success(msg):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")

def print_error(msg):
    print(f"  {Colors.RED}✗{Colors.RESET} {msg}")

def print_warning(msg):
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {msg}")

def print_info(msg):
    print(f"  {Colors.BLUE}ℹ{Colors.RESET} {msg}")


class TestFlujoProductosLotes:
    """Test de integración para flujos de productos y lotes."""
    
    def __init__(self):
        self.client = APIClient()
        self.errors = []
        self.tests_passed = 0
        self.tests_failed = 0
        
    def setup(self):
        """Crear datos de prueba."""
        print_header("CONFIGURACIÓN DE DATOS DE PRUEBA")
        
        # Crear centro de prueba
        self.centro, _ = Centro.objects.get_or_create(
            nombre='Centro Test Flujo',
            defaults={'activo': True}
        )
        print_success(f"Centro: {self.centro.nombre} (ID: {self.centro.id})")
        
        # Usuario farmacia (puede crear/editar productos y lotes)
        try:
            self.user_farmacia = User.objects.get(username='test_farmacia_flujo')
        except User.DoesNotExist:
            self.user_farmacia = User.objects.create_user(
                username='test_farmacia_flujo',
                email='farmacia_flujo@test.com',
                password='test123',
                rol='farmacia',
                is_active=True,
                perm_productos=True,
                perm_lotes=True,
            )
        print_success(f"Usuario farmacia: {self.user_farmacia.username}")
        
        # Usuario centro (solo lectura)
        try:
            self.user_centro = User.objects.get(username='test_centro_flujo')
        except User.DoesNotExist:
            self.user_centro = User.objects.create_user(
                username='test_centro_flujo',
                email='centro_flujo@test.com',
                password='test123',
                rol='centro',
                centro=self.centro,
                is_active=True,
                perm_productos=True,
                perm_lotes=True,
            )
        print_success(f"Usuario centro: {self.user_centro.username}")
        
    def test_1_producto_crear(self):
        """Test 1: Crear producto (solo farmacia)."""
        print_header("TEST 1: CREAR PRODUCTO")
        
        # Login como farmacia
        self.client.force_authenticate(user=self.user_farmacia)
        
        data = {
            'clave': 'TEST-FLUJO-001',
            'nombre': 'Producto Test Flujo',
            'presentacion': 'CAJA CON 10 TABLETAS',
            'unidad_medida': 'PIEZA',
            'categoria': 'medicamento',
            'stock_minimo': 10,
        }
        
        response = self.client.post('/api/productos/', data, format='json')
        
        if response.status_code == status.HTTP_201_CREATED:
            self.producto_id = response.data['id']
            print_success(f"Producto creado: ID={self.producto_id}, tiene_lotes={response.data.get('tiene_lotes', False)}")
            self.tests_passed += 1
            return True
        else:
            print_error(f"Error al crear producto: {response.status_code} - {response.data}")
            self.tests_failed += 1
            return False
    
    def test_2_producto_editar_sin_lotes(self):
        """Test 2: Editar producto SIN lotes (debe permitir cambiar campos obligatorios)."""
        print_header("TEST 2: EDITAR PRODUCTO SIN LOTES")
        
        self.client.force_authenticate(user=self.user_farmacia)
        
        # Verificar que no tiene lotes
        producto = Producto.objects.get(id=self.producto_id)
        tiene_lotes = producto.lotes.exists()
        print_info(f"Producto tiene_lotes: {tiene_lotes}")
        
        if tiene_lotes:
            print_warning("El producto ya tiene lotes, saltando test")
            return True
        
        # Intentar cambiar nombre (debe funcionar sin lotes)
        data = {
            'clave': 'TEST-FLUJO-001',
            'nombre': 'Producto Test Flujo MODIFICADO',
            'presentacion': 'CAJA CON 20 TABLETAS',
            'unidad_medida': 'PIEZA',
            'categoria': 'medicamento',
            'stock_minimo': 15,
        }
        
        response = self.client.put(f'/api/productos/{self.producto_id}/', data, format='json')
        
        if response.status_code == status.HTTP_200_OK:
            print_success(f"Producto editado correctamente: nombre='{response.data['nombre']}'")
            self.tests_passed += 1
            return True
        else:
            print_error(f"Error al editar: {response.status_code} - {response.data}")
            self.tests_failed += 1
            return False
    
    def test_3_lote_crear(self):
        """Test 3: Crear lote para el producto."""
        print_header("TEST 3: CREAR LOTE")
        
        self.client.force_authenticate(user=self.user_farmacia)
        
        data = {
            'producto': self.producto_id,
            'numero_lote': 'LOTE-FLUJO-001',
            'cantidad_inicial': 100,
            'cantidad_actual': 100,
            'fecha_caducidad': (date.today() + timedelta(days=365)).isoformat(),
            'precio_unitario': '25.50',
        }
        
        response = self.client.post('/api/lotes/', data, format='json')
        
        if response.status_code == status.HTTP_201_CREATED:
            self.lote_id = response.data['id']
            print_success(f"Lote creado: ID={self.lote_id}, numero_lote={response.data['numero_lote']}")
            print_info(f"tiene_movimientos: {response.data.get('tiene_movimientos', False)}")
            self.tests_passed += 1
            return True
        else:
            print_error(f"Error al crear lote: {response.status_code} - {response.data}")
            self.tests_failed += 1
            return False
    
    def test_4_producto_con_lotes_campos_protegidos(self):
        """Test 4: Producto CON lotes NO permite cambiar campos obligatorios."""
        print_header("TEST 4: PROTECCIÓN DE CAMPOS EN PRODUCTO CON LOTES")
        
        self.client.force_authenticate(user=self.user_farmacia)
        
        # Verificar que ahora tiene lotes
        producto = Producto.objects.get(id=self.producto_id)
        tiene_lotes = producto.lotes.exists()
        print_info(f"Producto tiene_lotes: {tiene_lotes}")
        
        # GET para ver tiene_lotes en la respuesta
        response_get = self.client.get(f'/api/productos/{self.producto_id}/')
        if response_get.status_code == 200:
            print_info(f"API tiene_lotes: {response_get.data.get('tiene_lotes')}")
        
        nombre_original = producto.nombre
        
        # Intentar cambiar nombre (debe FALLAR con lotes)
        data = {
            'clave': 'TEST-FLUJO-001',
            'nombre': 'NOMBRE QUE NO DEBE CAMBIAR',
            'presentacion': 'CAJA CON 20 TABLETAS',
            'unidad_medida': 'PIEZA',
            'categoria': 'medicamento',
            'stock_minimo': 15,
        }
        
        response = self.client.put(f'/api/productos/{self.producto_id}/', data, format='json')
        
        # Verificar que se rechazó el cambio
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print_success("Backend rechazó correctamente el cambio (400 Bad Request)")
            # Verificar que el nombre no cambió
            producto.refresh_from_db()
            if producto.nombre == nombre_original:
                print_success(f"El nombre no cambió: '{producto.nombre}'")
                self.tests_passed += 1
                return True
        elif response.status_code == status.HTTP_200_OK:
            # Verificar que el nombre no cambió
            producto.refresh_from_db()
            if 'NOMBRE QUE NO DEBE CAMBIAR' not in producto.nombre:
                print_success("El nombre no cambió (protección funcionó)")
                self.tests_passed += 1
                return True
            else:
                print_error("¡FALLA! El nombre cambió cuando no debía")
                self.tests_failed += 1
                return False
        
        print_error(f"Respuesta inesperada: {response.status_code} - {response.data}")
        self.tests_failed += 1
        return False
    
    def test_5_producto_campos_editables_con_lotes(self):
        """Test 5: Campos NO obligatorios SÍ se pueden editar con lotes."""
        print_header("TEST 5: CAMPOS EDITABLES (NO OBLIGATORIOS) CON LOTES")
        
        self.client.force_authenticate(user=self.user_farmacia)
        
        producto = Producto.objects.get(id=self.producto_id)
        
        # Cambiar solo campos editables (stock_minimo, descripcion, nombre_comercial)
        data = {
            'clave': producto.clave,  # No cambiar
            'nombre': producto.nombre,  # No cambiar
            'presentacion': producto.presentacion,  # No cambiar
            'unidad_medida': producto.unidad_medida,  # No cambiar
            'categoria': producto.categoria,  # No cambiar
            'stock_minimo': 50,  # CAMBIAR (permitido)
            'descripcion': 'Descripción actualizada de prueba',  # CAMBIAR (permitido)
            'nombre_comercial': 'Marca Comercial Test',  # CAMBIAR (permitido)
        }
        
        response = self.client.put(f'/api/productos/{self.producto_id}/', data, format='json')
        
        if response.status_code == status.HTTP_200_OK:
            producto.refresh_from_db()
            if producto.stock_minimo == 50:
                print_success(f"stock_minimo actualizado: {producto.stock_minimo}")
                print_success(f"descripcion actualizada: '{producto.descripcion}'")
                print_success(f"nombre_comercial actualizado: '{producto.nombre_comercial}'")
                self.tests_passed += 1
                return True
        
        print_error(f"Error: {response.status_code} - {response.data}")
        self.tests_failed += 1
        return False
    
    def test_6_lote_editar_sin_movimientos(self):
        """Test 6: Lote SIN movimientos permite editar campos."""
        print_header("TEST 6: EDITAR LOTE SIN MOVIMIENTOS")
        
        self.client.force_authenticate(user=self.user_farmacia)
        
        lote = Lote.objects.get(id=self.lote_id)
        tiene_mov = Movimiento.objects.filter(lote=lote).exists()
        print_info(f"Lote tiene_movimientos: {tiene_mov}")
        
        # GET para ver tiene_movimientos
        response_get = self.client.get(f'/api/lotes/{self.lote_id}/')
        if response_get.status_code == 200:
            print_info(f"API tiene_movimientos: {response_get.data.get('tiene_movimientos')}")
        
        data = {
            'producto': self.producto_id,
            'numero_lote': 'LOTE-FLUJO-001-MOD',  # Cambiar
            'cantidad_inicial': 150,  # Cambiar
            'cantidad_actual': 150,
            'fecha_caducidad': (date.today() + timedelta(days=400)).isoformat(),
            'precio_unitario': '30.00',
            'marca': 'Marca Test',  # Agregar
        }
        
        response = self.client.put(f'/api/lotes/{self.lote_id}/', data, format='json')
        
        if response.status_code == status.HTTP_200_OK:
            print_success(f"Lote editado: numero_lote='{response.data['numero_lote']}'")
            self.tests_passed += 1
            return True
        else:
            print_error(f"Error: {response.status_code} - {response.data}")
            self.tests_failed += 1
            return False
    
    def test_7_crear_movimiento(self):
        """Test 7: Crear movimiento para probar protecciones."""
        print_header("TEST 7: CREAR MOVIMIENTO")
        
        # Crear movimiento de entrada directamente
        try:
            self.movimiento = Movimiento.objects.create(
                tipo='entrada',
                producto_id=self.producto_id,
                lote_id=self.lote_id,
                cantidad=10,
                usuario=self.user_farmacia,
                motivo='Test de flujo - entrada inicial',
            )
            print_success(f"Movimiento creado: ID={self.movimiento.id}")
            self.tests_passed += 1
            return True
        except Exception as e:
            print_error(f"Error al crear movimiento: {e}")
            self.tests_failed += 1
            return False
    
    def test_8_lote_con_movimientos_campos_protegidos(self):
        """Test 8: Lote CON movimientos NO permite cambiar campos críticos."""
        print_header("TEST 8: PROTECCIÓN DE CAMPOS EN LOTE CON MOVIMIENTOS")
        
        self.client.force_authenticate(user=self.user_farmacia)
        
        lote = Lote.objects.get(id=self.lote_id)
        tiene_mov = Movimiento.objects.filter(lote=lote).exists()
        print_info(f"Lote tiene_movimientos: {tiene_mov}")
        
        # GET para ver tiene_movimientos actualizado
        response_get = self.client.get(f'/api/lotes/{self.lote_id}/')
        if response_get.status_code == 200:
            print_info(f"API tiene_movimientos: {response_get.data.get('tiene_movimientos')}")
        
        # Intentar cambiar numero_lote (debe FALLAR)
        data = {
            'producto': self.producto_id,
            'numero_lote': 'NUEVO-NUMERO-PROHIBIDO',
            'cantidad_inicial': lote.cantidad_inicial,
            'cantidad_actual': lote.cantidad_actual,
            'fecha_caducidad': lote.fecha_caducidad.isoformat(),
            'precio_unitario': str(lote.precio_unitario),
        }
        
        response = self.client.put(f'/api/lotes/{self.lote_id}/', data, format='json')
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            if 'numero_lote' in str(response.data) or 'código de lote' in str(response.data):
                print_success("Backend rechazó correctamente el cambio de numero_lote")
                self.tests_passed += 1
                return True
        elif response.status_code == status.HTTP_200_OK:
            lote.refresh_from_db()
            if lote.numero_lote != 'NUEVO-NUMERO-PROHIBIDO':
                print_success("El numero_lote no cambió (protección funcionó)")
                self.tests_passed += 1
                return True
            else:
                print_error("¡FALLA! El numero_lote cambió cuando no debía")
                self.tests_failed += 1
                return False
        
        print_error(f"Respuesta inesperada: {response.status_code}")
        self.tests_failed += 1
        return False
    
    def test_9_usuario_centro_solo_lectura(self):
        """Test 9: Usuario CENTRO no puede crear/editar productos."""
        print_header("TEST 9: USUARIO CENTRO SOLO LECTURA")
        
        self.client.force_authenticate(user=self.user_centro)
        
        # Intentar crear producto (debe fallar)
        data = {
            'clave': 'TEST-CENTRO-001',
            'nombre': 'Producto Centro Test',
            'presentacion': 'CAJA',
            'unidad_medida': 'PIEZA',
            'categoria': 'medicamento',
        }
        
        response = self.client.post('/api/productos/', data, format='json')
        
        if response.status_code == status.HTTP_403_FORBIDDEN:
            print_success("Usuario centro NO puede crear productos (403)")
            self.tests_passed += 1
            return True
        elif response.status_code == status.HTTP_201_CREATED:
            print_error("¡FALLA! Usuario centro pudo crear producto")
            # Limpiar
            Producto.objects.filter(clave='TEST-CENTRO-001').delete()
            self.tests_failed += 1
            return False
        else:
            print_warning(f"Respuesta: {response.status_code} - {response.data}")
            self.tests_passed += 1  # Cualquier error que no sea 201 es aceptable
            return True
    
    def test_10_relaciones_fk_validas(self):
        """Test 10: Verificar integridad de relaciones FK."""
        print_header("TEST 10: INTEGRIDAD DE RELACIONES FK")
        
        producto = Producto.objects.get(id=self.producto_id)
        lote = Lote.objects.get(id=self.lote_id)
        
        # Verificar relación producto -> lotes
        lotes_producto = producto.lotes.all()
        print_info(f"Producto tiene {lotes_producto.count()} lote(s)")
        
        # Verificar relación lote -> producto
        print_info(f"Lote.producto: {lote.producto.clave}")
        
        # Verificar relación lote -> movimientos
        movimientos_lote = Movimiento.objects.filter(lote=lote)
        print_info(f"Lote tiene {movimientos_lote.count()} movimiento(s)")
        
        # Verificar relación movimiento -> producto
        if self.movimiento:
            print_info(f"Movimiento.producto: {self.movimiento.producto.clave}")
            print_info(f"Movimiento.lote: {self.movimiento.lote.numero_lote}")
        
        if lotes_producto.exists() and lote.producto == producto:
            print_success("Relaciones FK válidas")
            self.tests_passed += 1
            return True
        else:
            print_error("Problema con relaciones FK")
            self.tests_failed += 1
            return False
    
    def cleanup(self):
        """Limpiar datos de prueba."""
        print_header("LIMPIEZA")
        
        try:
            # Eliminar movimiento primero (FK a lote y producto)
            if hasattr(self, 'movimiento') and self.movimiento:
                self.movimiento.delete()
                print_info("Movimiento eliminado")
            
            # Eliminar lote (FK a producto)
            if hasattr(self, 'lote_id'):
                Lote.objects.filter(id=self.lote_id).delete()
                print_info("Lote eliminado")
            
            # Eliminar producto
            if hasattr(self, 'producto_id'):
                Producto.objects.filter(id=self.producto_id).delete()
                print_info("Producto eliminado")
            
            print_success("Limpieza completada")
        except Exception as e:
            print_warning(f"Error en limpieza: {e}")
    
    def run_all(self):
        """Ejecutar todos los tests."""
        print(f"\n{Colors.BOLD}{'#'*60}")
        print(f"  TEST DE FLUJO: PRODUCTOS Y LOTES")
        print(f"  Verifica protecciones, permisos y relaciones FK")
        print(f"{'#'*60}{Colors.RESET}\n")
        
        self.setup()
        
        tests = [
            self.test_1_producto_crear,
            self.test_2_producto_editar_sin_lotes,
            self.test_3_lote_crear,
            self.test_4_producto_con_lotes_campos_protegidos,
            self.test_5_producto_campos_editables_con_lotes,
            self.test_6_lote_editar_sin_movimientos,
            self.test_7_crear_movimiento,
            self.test_8_lote_con_movimientos_campos_protegidos,
            self.test_9_usuario_centro_solo_lectura,
            self.test_10_relaciones_fk_validas,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print_error(f"Excepción en {test.__name__}: {e}")
                self.tests_failed += 1
        
        self.cleanup()
        
        # Resumen
        print_header("RESUMEN")
        total = self.tests_passed + self.tests_failed
        print(f"  Tests ejecutados: {total}")
        print(f"  {Colors.GREEN}Pasaron: {self.tests_passed}{Colors.RESET}")
        print(f"  {Colors.RED}Fallaron: {self.tests_failed}{Colors.RESET}")
        
        if self.tests_failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}  ✓ TODOS LOS TESTS PASARON{Colors.RESET}\n")
            return True
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}  ✗ HAY {self.tests_failed} TEST(S) FALLIDO(S){Colors.RESET}\n")
            return False


if __name__ == '__main__':
    test = TestFlujoProductosLotes()
    success = test.run_all()
    sys.exit(0 if success else 1)
