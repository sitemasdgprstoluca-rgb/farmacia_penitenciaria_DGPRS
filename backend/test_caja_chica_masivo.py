"""
Pruebas masivas del módulo Compras de Caja Chica
- Backend API (Django REST Framework)
- Base de datos (PostgreSQL/Supabase)
- Flujo completo: crear compra → autorizar → registrar compra → recibir → inventario → salidas

Ejecutar con: python test_caja_chica_masivo.py
"""

import os
import sys
import json
import random
import string
from datetime import datetime, timedelta
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from core.models import (
    User, Centro, Producto,
    CompraCajaChica, DetalleCompraCajaChica, 
    InventarioCajaChica, MovimientoCajaChica, 
    HistorialCompraCajaChica
)

# Alias para mantener compatibilidad
Usuario = User


class Colors:
    """Colores para output en terminal"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


class TestCajaChicaDatabase:
    """Pruebas de existencia y estructura de tablas"""
    
    def __init__(self):
        self.tables_required = [
            'compras_caja_chica',
            'detalle_compras_caja_chica',
            'inventario_caja_chica',
            'movimientos_caja_chica',
            'historial_compras_caja_chica'
        ]
        self.results = {'passed': 0, 'failed': 0, 'warnings': 0}
    
    def check_table_exists(self, table_name):
        """Verifica si una tabla existe"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, [table_name])
            return cursor.fetchone()[0]
    
    def check_all_tables(self):
        """Verifica todas las tablas requeridas"""
        print_header("VERIFICACIÓN DE TABLAS")
        
        all_exist = True
        for table in self.tables_required:
            if self.check_table_exists(table):
                print_success(f"Tabla '{table}' existe")
                self.results['passed'] += 1
            else:
                print_error(f"Tabla '{table}' NO existe")
                self.results['failed'] += 1
                all_exist = False
        
        return all_exist
    
    def check_table_columns(self, table_name, expected_columns):
        """Verifica columnas de una tabla"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = %s
            """, [table_name])
            existing_columns = [row[0] for row in cursor.fetchall()]
        
        missing = set(expected_columns) - set(existing_columns)
        if missing:
            print_warning(f"  Columnas faltantes en {table_name}: {missing}")
            self.results['warnings'] += 1
            return False
        return True
    
    def check_foreign_keys(self, table_name):
        """Verifica foreign keys de una tabla"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = %s
            """, [table_name])
            fks = cursor.fetchall()
        
        if fks:
            print_info(f"  Foreign keys en {table_name}:")
            for fk in fks:
                print(f"    - {fk[1]} → {fk[2]}")
        return len(fks) > 0
    
    def check_triggers(self):
        """Verifica triggers del módulo"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT trigger_name, event_object_table 
                FROM information_schema.triggers 
                WHERE trigger_schema = 'public'
                AND trigger_name LIKE '%caja_chica%'
            """)
            triggers = cursor.fetchall()
        
        if triggers:
            print_info("Triggers encontrados:")
            for t in triggers:
                print(f"  - {t[0]} en tabla {t[1]}")
            return True
        else:
            print_warning("No se encontraron triggers para caja chica")
            return False
    
    def run_all(self):
        """Ejecuta todas las verificaciones de DB"""
        tables_ok = self.check_all_tables()
        
        if not tables_ok:
            print_error("\n¡TABLAS NO ENCONTRADAS!")
            print_info("Debe ejecutar el SQL de migración en Supabase:")
            print_info("  Archivo: backend/migrations_sql/create_compras_caja_chica.sql")
            return False
        
        # Verificar estructura de tablas
        print_header("VERIFICACIÓN DE ESTRUCTURA")
        
        # Columnas esperadas por tabla
        expected_structure = {
            'compras_caja_chica': ['id', 'folio', 'centro_id', 'estado', 'motivo_compra', 'total'],
            'detalle_compras_caja_chica': ['id', 'compra_id', 'producto_id', 'cantidad_solicitada', 'precio_unitario'],
            'inventario_caja_chica': ['id', 'centro_id', 'producto_id', 'cantidad_actual'],
            'movimientos_caja_chica': ['id', 'inventario_id', 'tipo', 'cantidad'],
            'historial_compras_caja_chica': ['id', 'compra_id', 'accion', 'estado_anterior', 'estado_nuevo']
        }
        
        for table, columns in expected_structure.items():
            if self.check_table_exists(table):
                self.check_table_columns(table, columns)
                self.check_foreign_keys(table)
        
        self.check_triggers()
        
        return True


class TestCajaChicaAPI:
    """Pruebas de API REST"""
    
    def __init__(self):
        self.client = APIClient()
        self.results = {'passed': 0, 'failed': 0, 'errors': []}
        self.test_data = {}
    
    def setup_test_user(self, rol='administrador_centro'):
        """Configura usuario de prueba con autenticación"""
        # Buscar o crear usuario de prueba
        try:
            centro = Centro.objects.filter(activo=True).first()
            if not centro:
                print_error("No hay centros activos en la base de datos")
                return None
            
            # Buscar usuario admin primero
            user = Usuario.objects.filter(
                is_superuser=True,
                is_active=True
            ).first()
            
            if not user:
                # Buscar por rol
                user = Usuario.objects.filter(
                    rol__in=['admin', 'ADMIN', 'administrador', 'farmacia', 'FARMACIA'],
                    is_active=True
                ).first()
            
            if not user:
                # Cualquier usuario activo
                user = Usuario.objects.filter(is_active=True).first()
            
            if not user:
                print_error("No hay usuarios activos en la base de datos")
                return None
            
            # Asignar centro si no tiene
            if not user.centro_id:
                user.centro_id = centro.id
            else:
                centro = Centro.objects.filter(id=user.centro_id).first() or centro
            
            # Autenticar
            self.client.force_authenticate(user=user)
            self.test_data['user'] = user
            self.test_data['centro'] = centro
            
            print_success(f"Usuario autenticado: {user.username} (rol: {user.rol})")
            print_info(f"Centro: {centro.nombre}")
            return user
            
        except Exception as e:
            print_error(f"Error configurando usuario: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def test_list_compras(self):
        """Prueba listar compras de caja chica"""
        try:
            response = self.client.get('/api/compras-caja-chica/')
            if response.status_code == 200:
                print_success(f"GET /api/compras-caja-chica/ - OK ({len(response.data.get('results', []))} registros)")
                self.results['passed'] += 1
                return True
            else:
                print_error(f"GET /api/compras-caja-chica/ - Error {response.status_code}")
                self.results['failed'] += 1
                self.results['errors'].append(f"List compras: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"GET /api/compras-caja-chica/ - Excepción: {str(e)}")
            self.results['failed'] += 1
            return False
    
    def test_create_compra(self):
        """Prueba crear una compra de caja chica"""
        try:
            producto = Producto.objects.filter(activo=True).first()
            if not producto:
                print_warning("No hay productos activos para prueba")
                return None
            
            data = {
                'centro': self.test_data['centro'].id,
                'motivo_compra': f'Prueba masiva - {datetime.now().isoformat()}',
                'proveedor_nombre': 'Proveedor de Prueba',
                'observaciones': 'Generado por test_caja_chica_masivo.py',
                'detalles': [
                    {
                        'producto': producto.id,
                        'cantidad_solicitada': random.randint(5, 20),
                        'precio_unitario': str(round(random.uniform(50, 500), 2)),
                        'descripcion_producto': producto.nombre
                    }
                ]
            }
            
            response = self.client.post(
                '/api/compras-caja-chica/',
                data=json.dumps(data),
                content_type='application/json'
            )
            
            if response.status_code in [200, 201]:
                compra_id = response.data.get('id')
                self.test_data['compra_id'] = compra_id
                self.test_data['producto'] = producto
                print_success(f"POST /api/compras-caja-chica/ - Creada compra ID: {compra_id}")
                self.results['passed'] += 1
                return compra_id
            else:
                print_error(f"POST /api/compras-caja-chica/ - Error {response.status_code}: {response.data}")
                self.results['failed'] += 1
                return None
                
        except Exception as e:
            print_error(f"POST /api/compras-caja-chica/ - Excepción: {str(e)}")
            self.results['failed'] += 1
            return None
    
    def test_get_compra_detail(self, compra_id):
        """Prueba obtener detalle de compra"""
        try:
            response = self.client.get(f'/api/compras-caja-chica/{compra_id}/')
            if response.status_code == 200:
                print_success(f"GET /api/compras-caja-chica/{compra_id}/ - OK")
                print_info(f"  Estado: {response.data.get('estado')}")
                print_info(f"  Folio: {response.data.get('folio')}")
                self.results['passed'] += 1
                return response.data
            else:
                print_error(f"GET /api/compras-caja-chica/{compra_id}/ - Error {response.status_code}")
                self.results['failed'] += 1
                return None
        except Exception as e:
            print_error(f"GET /api/compras-caja-chica/{compra_id}/ - Excepción: {str(e)}")
            self.results['failed'] += 1
            return None
    
    def test_autorizar_compra(self, compra_id):
        """Prueba autorizar una compra"""
        try:
            data = {'observaciones': 'Autorizado en prueba masiva'}
            response = self.client.post(
                f'/api/compras-caja-chica/{compra_id}/autorizar/',
                data=json.dumps(data),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                print_success(f"POST /api/compras-caja-chica/{compra_id}/autorizar/ - OK")
                self.results['passed'] += 1
                return True
            else:
                print_error(f"POST autorizar - Error {response.status_code}: {response.data}")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print_error(f"POST autorizar - Excepción: {str(e)}")
            self.results['failed'] += 1
            return False
    
    def test_registrar_compra(self, compra_id):
        """Prueba registrar que la compra fue realizada"""
        try:
            data = {
                'numero_factura': f'FACT-{random.randint(1000, 9999)}',
                'fecha_compra': datetime.now().strftime('%Y-%m-%d'),
                'observaciones': 'Compra registrada en prueba masiva'
            }
            response = self.client.post(
                f'/api/compras-caja-chica/{compra_id}/registrar_compra/',
                data=json.dumps(data),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                print_success(f"POST /api/compras-caja-chica/{compra_id}/registrar_compra/ - OK")
                self.results['passed'] += 1
                return True
            else:
                print_error(f"POST registrar_compra - Error {response.status_code}: {response.data}")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print_error(f"POST registrar_compra - Excepción: {str(e)}")
            self.results['failed'] += 1
            return False
    
    def test_recibir_compra(self, compra_id):
        """Prueba marcar compra como recibida (actualiza inventario)"""
        try:
            data = {'observaciones': 'Recibido en prueba masiva'}
            response = self.client.post(
                f'/api/compras-caja-chica/{compra_id}/recibir/',
                data=json.dumps(data),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                print_success(f"POST /api/compras-caja-chica/{compra_id}/recibir/ - OK")
                print_info("  Inventario de caja chica actualizado")
                self.results['passed'] += 1
                return True
            else:
                print_error(f"POST recibir - Error {response.status_code}: {response.data}")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print_error(f"POST recibir - Excepción: {str(e)}")
            self.results['failed'] += 1
            return False
    
    def test_list_inventario(self):
        """Prueba listar inventario de caja chica"""
        try:
            response = self.client.get('/api/inventario-caja-chica/')
            if response.status_code == 200:
                results = response.data.get('results', response.data)
                if isinstance(results, list):
                    count = len(results)
                else:
                    count = results.get('count', 0) if isinstance(results, dict) else 0
                print_success(f"GET /api/inventario-caja-chica/ - OK ({count} registros)")
                self.results['passed'] += 1
                return results
            else:
                print_error(f"GET /api/inventario-caja-chica/ - Error {response.status_code}")
                self.results['failed'] += 1
                return None
        except Exception as e:
            print_error(f"GET /api/inventario-caja-chica/ - Excepción: {str(e)}")
            self.results['failed'] += 1
            return None
    
    def test_registrar_salida(self, inventario_id, cantidad=1):
        """Prueba registrar salida de inventario"""
        try:
            data = {
                'cantidad': cantidad,
                'motivo': 'Salida de prueba masiva',
                'destinatario': 'Paciente de Prueba'
            }
            response = self.client.post(
                f'/api/inventario-caja-chica/{inventario_id}/registrar_salida/',
                data=json.dumps(data),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                print_success(f"POST /api/inventario-caja-chica/{inventario_id}/registrar_salida/ - OK")
                self.results['passed'] += 1
                return True
            else:
                print_error(f"POST registrar_salida - Error {response.status_code}: {response.data}")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print_error(f"POST registrar_salida - Excepción: {str(e)}")
            self.results['failed'] += 1
            return False
    
    def test_list_movimientos(self):
        """Prueba listar movimientos de caja chica"""
        try:
            response = self.client.get('/api/movimientos-caja-chica/')
            if response.status_code == 200:
                results = response.data.get('results', [])
                print_success(f"GET /api/movimientos-caja-chica/ - OK ({len(results)} registros)")
                self.results['passed'] += 1
                return True
            else:
                print_error(f"GET /api/movimientos-caja-chica/ - Error {response.status_code}")
                self.results['failed'] += 1
                return False
        except Exception as e:
            print_error(f"GET /api/movimientos-caja-chica/ - Excepción: {str(e)}")
            self.results['failed'] += 1
            return False
    
    def test_cancelar_compra(self, compra_id=None):
        """Prueba cancelar una compra (crear nueva para cancelar)"""
        try:
            # Crear nueva compra para cancelar
            producto = Producto.objects.filter(activo=True).first()
            data = {
                'centro': self.test_data['centro'].id,
                'motivo_compra': 'Compra para cancelar en prueba',
                'proveedor_nombre': 'Proveedor Test',
                'detalles': [{
                    'producto': producto.id,
                    'cantidad_solicitada': 5,
                    'precio_unitario': '100.00',
                    'descripcion_producto': producto.nombre
                }]
            }
            
            response = self.client.post(
                '/api/compras-caja-chica/',
                data=json.dumps(data),
                content_type='application/json'
            )
            
            if response.status_code not in [200, 201]:
                print_warning("No se pudo crear compra para prueba de cancelación")
                return False
            
            cancel_id = response.data.get('id')
            
            # Cancelar
            cancel_data = {'motivo': 'Cancelado en prueba masiva'}
            response = self.client.post(
                f'/api/compras-caja-chica/{cancel_id}/cancelar/',
                data=json.dumps(cancel_data),
                content_type='application/json'
            )
            
            if response.status_code == 200:
                print_success(f"POST /api/compras-caja-chica/{cancel_id}/cancelar/ - OK")
                self.results['passed'] += 1
                return True
            else:
                print_error(f"POST cancelar - Error {response.status_code}: {response.data}")
                self.results['failed'] += 1
                return False
                
        except Exception as e:
            print_error(f"POST cancelar - Excepción: {str(e)}")
            self.results['failed'] += 1
            return False
    
    def run_workflow_test(self):
        """Ejecuta prueba de flujo completo"""
        print_header("PRUEBA DE FLUJO COMPLETO")
        
        # 1. Crear compra
        print_info("Paso 1: Crear compra de caja chica")
        compra_id = self.test_create_compra()
        if not compra_id:
            print_error("No se pudo continuar sin ID de compra")
            return False
        
        # 2. Ver detalle
        print_info("\nPaso 2: Verificar detalle de compra")
        detail = self.test_get_compra_detail(compra_id)
        
        # 3. Autorizar
        print_info("\nPaso 3: Autorizar compra")
        self.test_autorizar_compra(compra_id)
        
        # 4. Registrar compra realizada
        print_info("\nPaso 4: Registrar compra realizada")
        self.test_registrar_compra(compra_id)
        
        # 5. Recibir (actualiza inventario)
        print_info("\nPaso 5: Recibir compra (actualiza inventario)")
        self.test_recibir_compra(compra_id)
        
        # 6. Verificar inventario
        print_info("\nPaso 6: Verificar inventario actualizado")
        inventario = self.test_list_inventario()
        
        # 7. Registrar salida si hay inventario
        if inventario and len(inventario) > 0:
            print_info("\nPaso 7: Registrar salida de inventario")
            inv_item = inventario[0] if isinstance(inventario, list) else None
            if inv_item and inv_item.get('id'):
                self.test_registrar_salida(inv_item['id'])
        
        # 8. Ver movimientos
        print_info("\nPaso 8: Verificar movimientos registrados")
        self.test_list_movimientos()
        
        return True
    
    def run_all(self):
        """Ejecuta todas las pruebas de API"""
        print_header("PRUEBAS DE API REST")
        
        # Setup
        if not self.setup_test_user():
            print_error("No se pudo configurar usuario de prueba")
            return False
        
        # Pruebas básicas
        print_info("\n--- Pruebas de endpoints básicos ---")
        self.test_list_compras()
        self.test_list_inventario()
        self.test_list_movimientos()
        
        # Flujo completo
        self.run_workflow_test()
        
        # Prueba de cancelación
        print_info("\n--- Prueba de cancelación ---")
        self.test_cancelar_compra()
        
        return True


class TestCajaChicaMasivo:
    """Pruebas masivas de carga y rendimiento"""
    
    def __init__(self):
        self.client = APIClient()
        self.results = {'created': 0, 'failed': 0, 'time_total': 0}
    
    def setup(self):
        """Configuración inicial"""
        centro = Centro.objects.filter(activo=True).first()
        user = Usuario.objects.filter(
            rol__in=['administrador_centro', 'director_centro', 'admin'],
            is_active=True
        ).first()
        
        if not user or not centro:
            return False
        
        self.client.force_authenticate(user=user)
        self.centro = centro
        self.productos = list(Producto.objects.filter(activo=True)[:10])
        return True
    
    def create_multiple_compras(self, count=10):
        """Crea múltiples compras para prueba de carga"""
        print_header(f"PRUEBA MASIVA: CREAR {count} COMPRAS")
        
        import time
        start_time = time.time()
        
        for i in range(count):
            try:
                producto = random.choice(self.productos)
                data = {
                    'centro': self.centro.id,
                    'motivo_compra': f'Prueba masiva #{i+1}',
                    'proveedor_nombre': f'Proveedor {random.randint(1, 5)}',
                    'detalles': [{
                        'producto': producto.id,
                        'cantidad_solicitada': random.randint(1, 50),
                        'precio_unitario': str(round(random.uniform(10, 1000), 2)),
                        'descripcion_producto': producto.nombre
                    }]
                }
                
                response = self.client.post(
                    '/api/compras-caja-chica/',
                    data=json.dumps(data),
                    content_type='application/json'
                )
                
                if response.status_code in [200, 201]:
                    self.results['created'] += 1
                    if (i + 1) % 5 == 0:
                        print_info(f"  Creadas {i+1}/{count} compras...")
                else:
                    self.results['failed'] += 1
                    
            except Exception as e:
                self.results['failed'] += 1
        
        elapsed = time.time() - start_time
        self.results['time_total'] = elapsed
        
        print_success(f"\nResultados:")
        print_info(f"  Creadas exitosamente: {self.results['created']}")
        print_info(f"  Fallidas: {self.results['failed']}")
        print_info(f"  Tiempo total: {elapsed:.2f} segundos")
        print_info(f"  Promedio por compra: {elapsed/count:.3f} segundos")
    
    def run_all(self, count=10):
        """Ejecuta pruebas masivas"""
        if not self.setup():
            print_error("No se pudo configurar para pruebas masivas")
            return
        
        self.create_multiple_compras(count)


def run_migration_check():
    """Verifica si es necesario ejecutar la migración"""
    print_header("VERIFICACIÓN DE MIGRACIÓN")
    
    db_test = TestCajaChicaDatabase()
    tables_exist = db_test.check_all_tables()
    
    if not tables_exist:
        print_warning("\n" + "="*60)
        print_warning("ACCIÓN REQUERIDA: Ejecutar migración SQL")
        print_warning("="*60)
        print_info("\nPara crear las tablas necesarias, ejecute el siguiente SQL")
        print_info("en el editor SQL de Supabase:\n")
        print(f"{Colors.CYAN}  Archivo: backend/migrations_sql/create_compras_caja_chica.sql{Colors.ENDC}")
        print_info("\nPasos:")
        print_info("  1. Abra Supabase Dashboard")
        print_info("  2. Vaya a SQL Editor")
        print_info("  3. Copie y ejecute el contenido del archivo SQL")
        print_info("  4. Vuelva a ejecutar este script de pruebas")
        return False
    
    return True


def main():
    """Función principal"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     PRUEBAS MASIVAS - MÓDULO COMPRAS DE CAJA CHICA         ║")
    print("║                  Farmacia Penitenciaria                     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    
    # 1. Verificar tablas
    if not run_migration_check():
        return
    
    # 2. Pruebas de base de datos
    print_header("PRUEBAS DE BASE DE DATOS")
    db_test = TestCajaChicaDatabase()
    db_test.run_all()
    
    # 3. Pruebas de API
    api_test = TestCajaChicaAPI()
    api_test.run_all()
    
    # 4. Resumen
    print_header("RESUMEN DE RESULTADOS")
    
    total_passed = db_test.results['passed'] + api_test.results['passed']
    total_failed = db_test.results['failed'] + api_test.results['failed']
    
    print_info(f"Pruebas DB - Pasadas: {db_test.results['passed']}, Fallidas: {db_test.results['failed']}")
    print_info(f"Pruebas API - Pasadas: {api_test.results['passed']}, Fallidas: {api_test.results['failed']}")
    print_info(f"\nTOTAL: {total_passed} pasadas, {total_failed} fallidas")
    
    if total_failed == 0:
        print_success("\n¡TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
    else:
        print_warning(f"\nSe encontraron {total_failed} pruebas fallidas")
        if api_test.results['errors']:
            print_info("Errores de API:")
            for err in api_test.results['errors']:
                print(f"  - {err}")
    
    # Preguntar por pruebas masivas
    print_info("\n¿Desea ejecutar pruebas masivas de carga? (crear múltiples compras)")
    try:
        response = input("Ingrese número de compras a crear (0 para omitir): ")
        count = int(response)
        if count > 0:
            masivo_test = TestCajaChicaMasivo()
            masivo_test.run_all(count)
    except (ValueError, EOFError):
        print_info("Omitiendo pruebas masivas")


if __name__ == '__main__':
    main()
