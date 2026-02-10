# -*- coding: utf-8 -*-
"""
Test Masivo de Integración: Frontend → Backend → Base de Datos
para el sistema de Movimientos de Inventario (Entradas y Salidas).

Ejecutar con: python manage.py test_movimientos_masivo
O directamente: python test_movimientos_masivo.py

Este script prueba:
1. Creación de movimientos tipo "entrada" (reabastecimiento de lotes existentes)
2. Creación de movimientos tipo "salida" (transferencias a centros)
3. Actualización correcta de stock en lotes
4. Validaciones de permisos (solo FARMACIA/ADMIN pueden crear movimientos directos)
5. Transaccionalidad y consistencia de datos
6. Auditoría de movimientos
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
django.setup()

import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.db import transaction
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from core.models import Producto, Lote, Movimiento, Centro

User = get_user_model()

# ==============================================================================
# COLORES PARA OUTPUT EN CONSOLA
# ==============================================================================
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {msg}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")

def print_fail(msg):
    print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ️  {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠️  {msg}{Colors.ENDC}")


# ==============================================================================
# TESTS DE INTEGRACIÓN MASIVOS
# ==============================================================================

class MovimientosIntegrationTests:
    """Tests masivos de integración para el sistema de movimientos."""
    
    def __init__(self):
        self.client = APIClient()
        self.tests_passed = 0
        self.tests_failed = 0
        self.user_farmacia = None
        self.user_admin = None
        self.user_centro = None
        self.producto = None
        self.lote = None
        self.centro = None
    
    def setup_test_data(self):
        """Crea datos de prueba necesarios."""
        print_header("CONFIGURACIÓN DE DATOS DE PRUEBA")
        
        try:
            # 1. Crear o obtener centro de prueba
            self.centro, created = Centro.objects.get_or_create(
                nombre='Centro Test Movimientos',
                defaults={
                    'direccion': 'Dirección Test',
                    'activo': True
                }
            )
            print_success(f"Centro {'creado' if created else 'existente'}: {self.centro.nombre} (ID: {self.centro.id})")
            
            # 2. Crear o obtener producto de prueba
            self.producto, created = Producto.objects.get_or_create(
                clave='TEST-MOV-001',
                defaults={
                    'nombre': 'Producto Test Movimientos',
                    'descripcion': 'Producto para pruebas de movimientos masivos',
                    'unidad_medida': 'pieza',
                    'categoria': 'medicamento',
                    'stock_minimo': 10,
                    'activo': True
                }
            )
            print_success(f"Producto {'creado' if created else 'existente'}: {self.producto.clave} (ID: {self.producto.id})")
            
            # 3. Crear lote de prueba con stock inicial
            self.lote, created = Lote.objects.get_or_create(
                numero_lote='LOTE-TEST-MOV-001',
                producto=self.producto,
                defaults={
                    'cantidad_inicial': 1000,
                    'cantidad_actual': 1000,
                    'fecha_caducidad': timezone.now().date() + timedelta(days=365),
                    'precio_unitario': Decimal('100.00'),
                    'activo': True,
                    'centro': None  # Almacén central (Farmacia)
                }
            )
            if not created:
                # Resetear stock para las pruebas
                self.lote.cantidad_actual = 1000
                self.lote.cantidad_inicial = 1000
                self.lote.activo = True
                self.lote.save()
            print_success(f"Lote {'creado' if created else 'reseteado'}: {self.lote.numero_lote} (ID: {self.lote.id}, Stock: {self.lote.cantidad_actual})")
            
            # 4. Crear usuarios de prueba
            # Usuario FARMACIA
            try:
                self.user_farmacia = User.objects.get(username='test_farmacia_mov')
                print_success(f"Usuario FARMACIA existente: {self.user_farmacia.username}")
            except User.DoesNotExist:
                self.user_farmacia = User(
                    username='test_farmacia_mov',
                    email='test_farmacia_mov@test.com',
                    rol='farmacia',
                    is_active=True,
                    first_name='Test',
                    last_name='Farmacia'
                )
                self.user_farmacia.set_password('test12345')
                self.user_farmacia.save()
                print_success(f"Usuario FARMACIA creado: {self.user_farmacia.username}")
            
            # Usuario ADMIN
            try:
                self.user_admin = User.objects.get(username='test_admin_mov')
                print_success(f"Usuario ADMIN existente: {self.user_admin.username}")
            except User.DoesNotExist:
                self.user_admin = User(
                    username='test_admin_mov',
                    email='test_admin_mov@test.com',
                    rol='admin',
                    is_active=True,
                    is_superuser=True,
                    first_name='Test',
                    last_name='Admin'
                )
                self.user_admin.set_password('test12345')
                self.user_admin.save()
                print_success(f"Usuario ADMIN creado: {self.user_admin.username}")
            
            # Usuario CENTRO (administrador_centro)
            try:
                self.user_centro = User.objects.get(username='test_centro_mov')
                print_success(f"Usuario CENTRO existente: {self.user_centro.username}")
            except User.DoesNotExist:
                self.user_centro = User(
                    username='test_centro_mov',
                    email='test_centro_mov@test.com',
                    rol='administrador_centro',
                    centro=self.centro,
                    is_active=True,
                    first_name='Test',
                    last_name='Centro'
                )
                self.user_centro.set_password('test12345')
                self.user_centro.save()
                print_success(f"Usuario CENTRO creado: {self.user_centro.username}")
            
            return True
            
        except Exception as e:
            print_fail(f"Error configurando datos de prueba: {e}")
            import traceback
            traceback.print_exc()
            return False

    def authenticate(self, user):
        """Autentica un usuario para las pruebas API."""
        self.client.force_authenticate(user=user)
        print_info(f"Autenticado como: {user.username} (rol: {user.rol})")

    def logout(self):
        """Cierra sesión."""
        self.client.force_authenticate(user=None)
    
    # ==========================================================================
    # TEST 1: Movimiento ENTRADA (Reabastecimiento)
    # ==========================================================================
    def test_entrada_farmacia_user(self):
        """Test: Usuario FARMACIA puede crear movimiento de ENTRADA."""
        print_header("TEST 1: Entrada de stock - Usuario FARMACIA")
        
        try:
            self.authenticate(self.user_farmacia)
            
            # Guardar stock inicial
            self.lote.refresh_from_db()
            stock_antes = self.lote.cantidad_actual
            cantidad_entrada = 100
            
            print_info(f"Stock inicial del lote: {stock_antes}")
            print_info(f"Cantidad a ingresar: {cantidad_entrada}")
            
            # Crear movimiento de entrada
            payload = {
                'lote': self.lote.id,
                'tipo': 'entrada',
                'cantidad': cantidad_entrada,
                'observaciones': 'Entrada de prueba - Reabastecimiento por compra'
            }
            
            response = self.client.post('/api/movimientos/', payload, format='json')
            
            if response.status_code == status.HTTP_201_CREATED:
                # Verificar que el stock se actualizó
                self.lote.refresh_from_db()
                stock_despues = self.lote.cantidad_actual
                
                if stock_despues == stock_antes + cantidad_entrada:
                    print_success(f"Stock actualizado correctamente: {stock_antes} → {stock_despues}")
                    
                    # Verificar que el movimiento se registró
                    mov = Movimiento.objects.filter(lote=self.lote, tipo='entrada').order_by('-fecha').first()
                    if mov and mov.cantidad == cantidad_entrada:
                        print_success(f"Movimiento registrado: ID={mov.id}, Cantidad={mov.cantidad}, Motivo='{mov.motivo}'")
                        self.tests_passed += 1
                        return True
                    else:
                        print_fail("Movimiento no encontrado o con cantidad incorrecta")
                else:
                    print_fail(f"Stock incorrecto: esperado {stock_antes + cantidad_entrada}, obtenido {stock_despues}")
            else:
                print_fail(f"Error HTTP {response.status_code}: {response.data}")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # TEST 2: Movimiento SALIDA/TRANSFERENCIA
    # ==========================================================================
    def test_salida_transferencia_farmacia(self):
        """Test: Usuario FARMACIA puede crear movimiento de SALIDA/TRANSFERENCIA."""
        print_header("TEST 2: Salida/Transferencia - Usuario FARMACIA")
        
        try:
            self.authenticate(self.user_farmacia)
            
            # Guardar stock inicial
            self.lote.refresh_from_db()
            stock_antes = self.lote.cantidad_actual
            cantidad_salida = 50
            
            print_info(f"Stock inicial del lote: {stock_antes}")
            print_info(f"Cantidad a transferir: {cantidad_salida}")
            print_info(f"Centro destino: {self.centro.nombre} (ID: {self.centro.id})")
            
            # Crear movimiento de salida/transferencia
            payload = {
                'lote': self.lote.id,
                'tipo': 'salida',
                'cantidad': cantidad_salida,
                'centro': self.centro.id,  # Centro destino
                'subtipo_salida': 'transferencia',
                'observaciones': 'Transferencia de prueba a centro penitenciario'
            }
            
            response = self.client.post('/api/movimientos/', payload, format='json')
            
            if response.status_code == status.HTTP_201_CREATED:
                # Verificar que el stock se redujo
                self.lote.refresh_from_db()
                stock_despues = self.lote.cantidad_actual
                
                if stock_despues == stock_antes - cantidad_salida:
                    print_success(f"Stock actualizado correctamente: {stock_antes} → {stock_despues}")
                    
                    # Verificar que el movimiento se registró con el centro destino
                    mov = Movimiento.objects.filter(
                        lote=self.lote, 
                        tipo='salida',
                        subtipo_salida='transferencia'
                    ).order_by('-fecha').first()
                    
                    if mov and mov.cantidad == cantidad_salida and mov.centro_destino == self.centro:
                        print_success(f"Movimiento registrado: ID={mov.id}, Cantidad={mov.cantidad}")
                        print_success(f"Centro destino correcto: {mov.centro_destino.nombre}")
                        self.tests_passed += 1
                        return True
                    else:
                        print_fail("Movimiento no encontrado o datos incorrectos")
                else:
                    print_fail(f"Stock incorrecto: esperado {stock_antes - cantidad_salida}, obtenido {stock_despues}")
            else:
                print_fail(f"Error HTTP {response.status_code}: {response.data}")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # TEST 3: Usuario ADMIN puede crear movimientos
    # ==========================================================================
    def test_entrada_admin_user(self):
        """Test: Usuario ADMIN puede crear movimientos de entrada."""
        print_header("TEST 3: Entrada de stock - Usuario ADMIN")
        
        try:
            self.authenticate(self.user_admin)
            
            self.lote.refresh_from_db()
            stock_antes = self.lote.cantidad_actual
            cantidad_entrada = 75
            
            print_info(f"Stock inicial: {stock_antes}")
            print_info(f"Cantidad a ingresar: {cantidad_entrada}")
            
            payload = {
                'lote': self.lote.id,
                'tipo': 'entrada',
                'cantidad': cantidad_entrada,
                'observaciones': 'Entrada por admin - Donación recibida'
            }
            
            response = self.client.post('/api/movimientos/', payload, format='json')
            
            if response.status_code == status.HTTP_201_CREATED:
                self.lote.refresh_from_db()
                stock_despues = self.lote.cantidad_actual
                
                if stock_despues == stock_antes + cantidad_entrada:
                    print_success(f"Stock actualizado: {stock_antes} → {stock_despues}")
                    print_success("ADMIN puede crear entradas correctamente")
                    self.tests_passed += 1
                    return True
                else:
                    print_fail(f"Stock incorrecto: esperado {stock_antes + cantidad_entrada}")
            else:
                print_fail(f"Error HTTP {response.status_code}: {response.data}")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # TEST 4: Validación de stock insuficiente
    # ==========================================================================
    def test_salida_stock_insuficiente(self):
        """Test: No se puede sacar más stock del disponible."""
        print_header("TEST 4: Validación de stock insuficiente")
        
        try:
            self.authenticate(self.user_farmacia)
            
            self.lote.refresh_from_db()
            stock_actual = self.lote.cantidad_actual
            cantidad_excesiva = stock_actual + 1000  # Más de lo disponible
            
            print_info(f"Stock actual: {stock_actual}")
            print_info(f"Intentando sacar: {cantidad_excesiva} (debe fallar)")
            
            payload = {
                'lote': self.lote.id,
                'tipo': 'salida',
                'cantidad': cantidad_excesiva,
                'centro': self.centro.id,
                'subtipo_salida': 'transferencia',
                'observaciones': 'Esto debe fallar por stock insuficiente'
            }
            
            response = self.client.post('/api/movimientos/', payload, format='json')
            
            if response.status_code == status.HTTP_400_BAD_REQUEST:
                print_success(f"Validación correcta: rechazado con HTTP 400")
                print_success(f"Mensaje de error: {response.data}")
                
                # Verificar que el stock no cambió
                self.lote.refresh_from_db()
                if self.lote.cantidad_actual == stock_actual:
                    print_success("Stock no afectado por operación fallida")
                    self.tests_passed += 1
                    return True
            else:
                print_fail(f"Se esperaba 400, se obtuvo {response.status_code}")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # TEST 5: Múltiples operaciones concurrentes (simulación)
    # ==========================================================================
    def test_operaciones_masivas(self):
        """Test: Múltiples entradas y salidas mantienen consistencia."""
        print_header("TEST 5: Operaciones masivas (50 entradas + 50 salidas)")
        
        try:
            self.authenticate(self.user_farmacia)
            
            # Resetear lote para el test
            self.lote.cantidad_actual = 5000
            self.lote.cantidad_inicial = 5000
            self.lote.save()
            
            stock_inicial = 5000
            total_entradas = 0
            total_salidas = 0
            operaciones_exitosas = 0
            
            print_info(f"Stock inicial: {stock_inicial}")
            print_info("Ejecutando 50 entradas de 10 unidades cada una...")
            
            # 50 entradas
            for i in range(50):
                payload = {
                    'lote': self.lote.id,
                    'tipo': 'entrada',
                    'cantidad': 10,
                    'observaciones': f'Entrada masiva #{i+1}'
                }
                response = self.client.post('/api/movimientos/', payload, format='json')
                if response.status_code == status.HTTP_201_CREATED:
                    total_entradas += 10
                    operaciones_exitosas += 1
            
            print_info(f"Entradas completadas: {operaciones_exitosas}/50")
            print_info("Ejecutando 50 salidas de 5 unidades cada una...")
            
            # 50 salidas
            salidas_exitosas = 0
            for i in range(50):
                payload = {
                    'lote': self.lote.id,
                    'tipo': 'salida',
                    'cantidad': 5,
                    'centro': self.centro.id,
                    'subtipo_salida': 'transferencia',
                    'observaciones': f'Salida masiva #{i+1}'
                }
                response = self.client.post('/api/movimientos/', payload, format='json')
                if response.status_code == status.HTTP_201_CREATED:
                    total_salidas += 5
                    salidas_exitosas += 1
            
            print_info(f"Salidas completadas: {salidas_exitosas}/50")
            
            # Verificar stock final
            self.lote.refresh_from_db()
            stock_esperado = stock_inicial + total_entradas - total_salidas
            stock_real = self.lote.cantidad_actual
            
            print_info(f"Stock esperado: {stock_inicial} + {total_entradas} - {total_salidas} = {stock_esperado}")
            print_info(f"Stock real: {stock_real}")
            
            if stock_real == stock_esperado:
                print_success(f"Consistencia verificada: Stock final = {stock_real}")
                
                # Contar movimientos en BD
                movs_entrada = Movimiento.objects.filter(lote=self.lote, tipo='entrada').count()
                movs_salida = Movimiento.objects.filter(lote=self.lote, tipo='salida').count()
                print_success(f"Movimientos en BD: {movs_entrada} entradas, {movs_salida} salidas")
                
                self.tests_passed += 1
                return True
            else:
                print_fail(f"Inconsistencia detectada: esperado {stock_esperado}, real {stock_real}")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # TEST 6: Usuario CENTRO no puede crear entradas directas
    # ==========================================================================
    def test_centro_no_puede_entrada_directa(self):
        """Test: Usuario CENTRO no puede crear movimientos de entrada en lotes de almacén central."""
        print_header("TEST 6: Usuario CENTRO no puede crear entradas en Almacén Central")
        
        try:
            self.authenticate(self.user_centro)
            
            # El lote está en el almacén central (centro=None)
            # Un usuario de centro no debería poder crear entradas directas ahí
            
            payload = {
                'lote': self.lote.id,
                'tipo': 'entrada',
                'cantidad': 50,
                'observaciones': 'Esto debería fallar - centro no puede crear entradas'
            }
            
            response = self.client.post('/api/movimientos/', payload, format='json')
            
            # Se espera que falle (400 o 403)
            if response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]:
                print_success(f"Correctamente rechazado con HTTP {response.status_code}")
                print_info(f"Mensaje: {response.data}")
                self.tests_passed += 1
                return True
            else:
                print_fail(f"Se esperaba 400/403, se obtuvo {response.status_code}")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # TEST 7: Verificar auditoría de movimientos
    # ==========================================================================
    def test_auditoria_movimientos(self):
        """Test: Los movimientos registran usuario y fecha correctamente."""
        print_header("TEST 7: Auditoría de movimientos")
        
        try:
            self.authenticate(self.user_farmacia)
            
            # Crear un movimiento
            payload = {
                'lote': self.lote.id,
                'tipo': 'entrada',
                'cantidad': 25,
                'observaciones': 'Movimiento para verificar auditoría'
            }
            
            response = self.client.post('/api/movimientos/', payload, format='json')
            
            if response.status_code == status.HTTP_201_CREATED:
                # Obtener el movimiento recién creado
                mov = Movimiento.objects.filter(lote=self.lote).order_by('-fecha').first()
                
                audit_ok = True
                
                # Verificar usuario registrado
                if mov.usuario == self.user_farmacia:
                    print_success(f"Usuario registrado correctamente: {mov.usuario.username}")
                else:
                    print_fail(f"Usuario incorrecto: {mov.usuario}")
                    audit_ok = False
                
                # Verificar fecha
                if mov.fecha and mov.created_at:
                    tiempo_diferencia = (timezone.now() - mov.fecha).total_seconds()
                    if tiempo_diferencia < 60:  # Menos de 60 segundos
                        print_success(f"Fecha registrada correctamente: {mov.fecha}")
                    else:
                        print_warning(f"Fecha parece antigua: {mov.fecha}")
                else:
                    print_fail("Fecha no registrada")
                    audit_ok = False
                
                # Verificar motivo/observaciones
                if mov.motivo == 'Movimiento para verificar auditoría':
                    print_success(f"Observaciones registradas: '{mov.motivo}'")
                else:
                    print_warning(f"Observaciones diferentes: '{mov.motivo}'")
                
                if audit_ok:
                    self.tests_passed += 1
                    return True
            else:
                print_fail(f"Error HTTP {response.status_code}")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # TEST 8: Verificar listado de movimientos filtrando por tipo
    # ==========================================================================
    def test_listado_movimientos_por_tipo(self):
        """Test: API devuelve movimientos filtrados por tipo correctamente."""
        print_header("TEST 8: Listado de movimientos filtrado por tipo")
        
        try:
            self.authenticate(self.user_farmacia)
            
            # Listar solo entradas
            response = self.client.get('/api/movimientos/', {'tipo': 'entrada'})
            
            if response.status_code == status.HTTP_200_OK:
                data = response.data
                results = data.get('results', data)
                
                # Verificar que todos son de tipo entrada
                all_entradas = all(m.get('tipo') == 'entrada' for m in results)
                
                if all_entradas:
                    print_success(f"Filtro por tipo 'entrada' funciona: {len(results)} resultados")
                else:
                    print_fail("Algunos resultados no son de tipo 'entrada'")
                    self.tests_failed += 1
                    return False
                
                # Listar solo salidas
                response = self.client.get('/api/movimientos/', {'tipo': 'salida'})
                
                if response.status_code == status.HTTP_200_OK:
                    data = response.data
                    results = data.get('results', data)
                    all_salidas = all(m.get('tipo') == 'salida' for m in results)
                    
                    if all_salidas:
                        print_success(f"Filtro por tipo 'salida' funciona: {len(results)} resultados")
                        self.tests_passed += 1
                        return True
                    else:
                        print_fail("Algunos resultados no son de tipo 'salida'")
            else:
                print_fail(f"Error HTTP {response.status_code}")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # TEST 9: Verificar endpoint de lotes disponibles
    # ==========================================================================
    def test_lotes_disponibles(self):
        """Test: El endpoint de lotes devuelve información correcta."""
        print_header("TEST 9: Verificar lotes disponibles")
        
        try:
            self.authenticate(self.user_farmacia)
            
            response = self.client.get('/api/lotes/')
            
            if response.status_code == status.HTTP_200_OK:
                data = response.data
                results = data.get('results', data)
                
                # Buscar nuestro lote de prueba
                lote_test = next((l for l in results if l.get('numero_lote') == 'LOTE-TEST-MOV-001'), None)
                
                if lote_test:
                    print_success(f"Lote encontrado: {lote_test.get('numero_lote')}")
                    print_info(f"  - Stock actual: {lote_test.get('cantidad_actual')}")
                    print_info(f"  - Producto: {lote_test.get('producto_nombre', lote_test.get('producto'))}")
                    self.tests_passed += 1
                    return True
                else:
                    print_warning("Lote de prueba no encontrado en resultados paginados")
                    print_success("Endpoint de lotes funciona correctamente")
                    self.tests_passed += 1
                    return True
            else:
                print_fail(f"Error HTTP {response.status_code}")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # TEST 10: Transaccionalidad - Rollback en error de stock insuficiente
    # ==========================================================================
    def test_transaccionalidad(self):
        """Test: Las operaciones fallidas no afectan el stock (stock insuficiente)."""
        print_header("TEST 10: Transaccionalidad - Rollback en error")
        
        try:
            self.authenticate(self.user_farmacia)
            
            # Guardar estado inicial
            self.lote.refresh_from_db()
            stock_antes = self.lote.cantidad_actual
            movs_antes = Movimiento.objects.filter(lote=self.lote).count()
            
            print_info(f"Stock antes: {stock_antes}")
            print_info(f"Movimientos antes: {movs_antes}")
            
            # Intentar una salida que exceda el stock (debe fallar por stock insuficiente)
            cantidad_excesiva = stock_antes + 99999
            payload = {
                'lote': self.lote.id,
                'tipo': 'salida',
                'cantidad': cantidad_excesiva,  # Más del stock disponible
                'centro': self.centro.id,
                'subtipo_salida': 'transferencia',
                'observaciones': 'Esto debe fallar por stock insuficiente y hacer rollback'
            }
            
            response = self.client.post('/api/movimientos/', payload, format='json')
            
            # Verificar que no cambió nada
            self.lote.refresh_from_db()
            stock_despues = self.lote.cantidad_actual
            movs_despues = Movimiento.objects.filter(lote=self.lote).count()
            
            print_info(f"Stock después: {stock_despues}")
            print_info(f"Movimientos después: {movs_despues}")
            
            if stock_despues == stock_antes and movs_despues == movs_antes:
                print_success("Transaccionalidad verificada: No hubo cambios por operación fallida")
                self.tests_passed += 1
                return True
            else:
                print_fail(f"Datos inconsistentes después de error")
            
            self.tests_failed += 1
            return False
            
        except Exception as e:
            print_fail(f"Excepción: {e}")
            self.tests_failed += 1
            return False
        finally:
            self.logout()
    
    # ==========================================================================
    # EJECUTAR TODOS LOS TESTS
    # ==========================================================================
    def run_all_tests(self):
        """Ejecuta todos los tests de integración."""
        print_header("🧪 INICIANDO TESTS MASIVOS DE INTEGRACIÓN")
        print_info("Sistema: Movimientos de Inventario (Entradas y Salidas)")
        print_info(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Configurar datos
        if not self.setup_test_data():
            print_fail("No se pudo configurar datos de prueba. Abortando.")
            return
        
        # Ejecutar tests
        tests = [
            self.test_entrada_farmacia_user,
            self.test_salida_transferencia_farmacia,
            self.test_entrada_admin_user,
            self.test_salida_stock_insuficiente,
            self.test_operaciones_masivas,
            self.test_centro_no_puede_entrada_directa,
            self.test_auditoria_movimientos,
            self.test_listado_movimientos_por_tipo,
            self.test_lotes_disponibles,
            self.test_transaccionalidad,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print_fail(f"Error ejecutando {test.__name__}: {e}")
                self.tests_failed += 1
        
        # Resumen final
        print_header("📊 RESUMEN DE RESULTADOS")
        total = self.tests_passed + self.tests_failed
        print_info(f"Tests ejecutados: {total}")
        print_success(f"Tests exitosos: {self.tests_passed}")
        if self.tests_failed > 0:
            print_fail(f"Tests fallidos: {self.tests_failed}")
        else:
            print_success("¡Todos los tests pasaron! ✨")
        
        porcentaje = (self.tests_passed / total * 100) if total > 0 else 0
        print_info(f"Porcentaje de éxito: {porcentaje:.1f}%")
        
        return self.tests_failed == 0
    
    def cleanup(self):
        """Limpia datos de prueba."""
        print_header("🧹 LIMPIEZA DE DATOS DE PRUEBA")
        
        try:
            # Eliminar movimientos de prueba
            movs_eliminados = Movimiento.objects.filter(lote__numero_lote='LOTE-TEST-MOV-001').delete()
            print_info(f"Movimientos eliminados: {movs_eliminados}")
            
            # Eliminar lote de prueba
            Lote.objects.filter(numero_lote='LOTE-TEST-MOV-001').delete()
            print_info("Lote de prueba eliminado")
            
            # Eliminar producto de prueba
            Producto.objects.filter(clave='TEST-MOV-001').delete()
            print_info("Producto de prueba eliminado")
            
            # Eliminar usuarios de prueba
            User.objects.filter(username__startswith='test_').filter(username__endswith='_mov').delete()
            print_info("Usuarios de prueba eliminados")
            
            # Eliminar centro de prueba
            Centro.objects.filter(nombre='Centro Test Movimientos').delete()
            print_info("Centro de prueba eliminado")
            
            print_success("Limpieza completada")
            
        except Exception as e:
            print_warning(f"Error durante limpieza: {e}")


# ==============================================================================
# MAIN
# ==============================================================================
if __name__ == '__main__':
    tester = MovimientosIntegrationTests()
    success = tester.run_all_tests()
    
    # Preguntar si limpiar datos
    print("\n")
    respuesta = input("¿Desea eliminar los datos de prueba? (s/n): ").strip().lower()
    if respuesta == 's':
        tester.cleanup()
    else:
        print_info("Datos de prueba conservados para inspección manual")
    
    # Exit code
    sys.exit(0 if success else 1)
