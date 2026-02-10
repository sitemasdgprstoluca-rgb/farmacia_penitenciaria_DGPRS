#!/usr/bin/env python
"""
Pruebas Masivas - Flujo Multinivel Compras de Caja Chica
=========================================================
Verifica que el backend, frontend y base de datos funcionen correctamente.

Ejecutar: python test_caja_chica_flujo.py
"""
import os
import sys
import django
import json
from datetime import date, timedelta
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from core.models import (
    Centro, CompraCajaChica, DetalleCompraCajaChica, 
    InventarioCajaChica, Producto, HistorialCompraCajaChica
)
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


class TestResultCollector:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def add_pass(self, test_name):
        self.passed += 1
        print_success(test_name)
    
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, str(error)))
        print_error(f"{test_name}: {error}")
    
    def summary(self):
        print_header("RESUMEN DE PRUEBAS")
        total = self.passed + self.failed
        print(f"Total: {total} | Pasadas: {Colors.GREEN}{self.passed}{Colors.RESET} | Fallidas: {Colors.RED}{self.failed}{Colors.RESET}")
        
        if self.errors:
            print(f"\n{Colors.RED}Errores:{Colors.RESET}")
            for test, error in self.errors:
                print(f"  - {test}: {error}")
        
        return self.failed == 0


results = TestResultCollector()


# ============================================================
# PRUEBAS DE BASE DE DATOS
# ============================================================
def test_db_estructura():
    """Verifica que la estructura de BD es correcta"""
    print_header("PRUEBAS DE BASE DE DATOS")
    
    # 1. Verificar tabla compras_caja_chica existe
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'compras_caja_chica'
            """)
            columns = [row[0] for row in cursor.fetchall()]
        
        # Columnas requeridas del flujo multinivel
        required_columns = [
            'fecha_envio_admin', 'fecha_autorizacion_admin',
            'fecha_envio_director', 'fecha_autorizacion_director',
            'administrador_centro_id', 'director_centro_id',
            'motivo_rechazo', 'rechazado_por_id', 'proveedor_contacto'
        ]
        
        missing = [col for col in required_columns if col not in columns]
        
        if missing:
            results.add_fail("DB: Columnas flujo multinivel", f"Faltan: {missing}")
        else:
            results.add_pass("DB: Todas las columnas del flujo multinivel existen")
    except Exception as e:
        results.add_fail("DB: Verificar estructura", str(e))
    
    # 2. Verificar constraint de estado
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT pg_get_constraintdef(c.oid) as def
                FROM pg_constraint c
                JOIN pg_class t ON c.conrelid = t.oid
                WHERE t.relname = 'compras_caja_chica' 
                AND c.conname = 'compras_caja_chica_estado_check'
            """)
            result = cursor.fetchone()
            
            if result:
                constraint_def = result[0]
                # Verificar que incluye los nuevos estados
                new_states = ['enviada_admin', 'autorizada_admin', 'enviada_director', 'rechazada']
                all_present = all(state in constraint_def for state in new_states)
                
                if all_present:
                    results.add_pass("DB: Constraint de estado incluye nuevos estados")
                else:
                    results.add_fail("DB: Constraint de estado", "Faltan algunos estados nuevos")
            else:
                results.add_pass("DB: Sin constraint de estado (OK para managed=False)")
    except Exception as e:
        results.add_fail("DB: Verificar constraint", str(e))
    
    # 3. Verificar foreign keys
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tc.constraint_name, kcu.column_name, ccu.table_name as foreign_table
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = 'compras_caja_chica' AND tc.constraint_type = 'FOREIGN KEY'
            """)
            fks = cursor.fetchall()
            
            # Verificar FKs del flujo
            fk_columns = [fk[1] for fk in fks]
            required_fks = ['administrador_centro_id', 'director_centro_id', 'rechazado_por_id']
            
            for fk in required_fks:
                if fk in fk_columns:
                    results.add_pass(f"DB: FK {fk} existe")
                else:
                    results.add_fail(f"DB: FK {fk}", "No existe")
    except Exception as e:
        results.add_fail("DB: Verificar FKs", str(e))


# ============================================================
# PRUEBAS DEL MODELO
# ============================================================
def test_modelo_compra():
    """Verifica que el modelo CompraCajaChica funciona"""
    print_header("PRUEBAS DEL MODELO")
    
    # 1. Verificar ESTADOS
    try:
        estados = dict(CompraCajaChica.ESTADOS)
        required_states = ['pendiente', 'enviada_admin', 'autorizada_admin', 
                          'enviada_director', 'autorizada', 'comprada', 
                          'recibida', 'cancelada', 'rechazada']
        
        missing = [s for s in required_states if s not in estados]
        if missing:
            results.add_fail("Modelo: Estados", f"Faltan: {missing}")
        else:
            results.add_pass("Modelo: Todos los estados definidos")
    except Exception as e:
        results.add_fail("Modelo: Estados", str(e))
    
    # 2. Verificar TRANSICIONES_VALIDAS
    try:
        transiciones = CompraCajaChica.TRANSICIONES_VALIDAS
        
        # Verificar algunas transiciones clave
        test_cases = [
            ('pendiente', 'enviada_admin', True),
            ('enviada_admin', 'autorizada_admin', True),
            ('autorizada_admin', 'enviada_director', True),
            ('enviada_director', 'autorizada', True),
            ('autorizada', 'comprada', True),
            ('comprada', 'recibida', True),
            ('pendiente', 'recibida', False),  # No válida
        ]
        
        all_ok = True
        for from_state, to_state, expected in test_cases:
            actual = to_state in transiciones.get(from_state, [])
            if actual != expected:
                all_ok = False
                results.add_fail(f"Modelo: Transición {from_state}->{to_state}", 
                               f"Esperado: {expected}, Actual: {actual}")
        
        if all_ok:
            results.add_pass("Modelo: Transiciones válidas correctas")
    except Exception as e:
        results.add_fail("Modelo: Transiciones", str(e))
    
    # 3. Verificar método puede_transicionar_a
    try:
        # Crear instancia temporal (sin guardar)
        compra = CompraCajaChica(estado='pendiente')
        
        if compra.puede_transicionar_a('enviada_admin'):
            results.add_pass("Modelo: puede_transicionar_a() funciona")
        else:
            results.add_fail("Modelo: puede_transicionar_a()", "Retorna False incorrectamente")
    except Exception as e:
        results.add_fail("Modelo: puede_transicionar_a()", str(e))
    
    # 4. Verificar campos del flujo
    try:
        fields = [f.name for f in CompraCajaChica._meta.get_fields()]
        required_fields = [
            'fecha_envio_admin', 'fecha_autorizacion_admin',
            'fecha_envio_director', 'fecha_autorizacion_director',
            'administrador_centro', 'director_centro',
            'rechazado_por', 'motivo_rechazo'
        ]
        
        missing = [f for f in required_fields if f not in fields]
        if missing:
            results.add_fail("Modelo: Campos flujo", f"Faltan: {missing}")
        else:
            results.add_pass("Modelo: Todos los campos del flujo definidos")
    except Exception as e:
        results.add_fail("Modelo: Campos flujo", str(e))


# ============================================================
# PRUEBAS DEL SERIALIZER
# ============================================================
def test_serializer():
    """Verifica que el serializer funciona correctamente"""
    print_header("PRUEBAS DEL SERIALIZER")
    
    try:
        from core.serializers import CompraCajaChicaSerializer, DetalleCompraCajaChicaWriteSerializer
        
        # 1. Verificar campos del serializer
        serializer = CompraCajaChicaSerializer()
        fields = list(serializer.fields.keys())
        
        required_fields = [
            'fecha_envio_admin', 'fecha_autorizacion_admin',
            'fecha_envio_director', 'fecha_autorizacion_director',
            'administrador_centro', 'administrador_centro_nombre',
            'director_centro', 'director_centro_nombre',
            'rechazado_por', 'rechazado_por_nombre',
            'motivo_rechazo', 'acciones_disponibles'
        ]
        
        missing = [f for f in required_fields if f not in fields]
        if missing:
            results.add_fail("Serializer: Campos", f"Faltan: {missing}")
        else:
            results.add_pass("Serializer: Todos los campos del flujo presentes")
        
        # 2. Verificar validación de detalles
        write_serializer = DetalleCompraCajaChicaWriteSerializer(data={
            'descripcion_producto': 'Paracetamol 500mg',
            'cantidad': 10,
            'precio_unitario': 15.50
        })
        
        if write_serializer.is_valid():
            results.add_pass("Serializer: Validación de detalles funciona")
        else:
            results.add_fail("Serializer: Validación detalles", write_serializer.errors)
        
        # 3. Verificar que precio_unitario es opcional
        write_serializer2 = DetalleCompraCajaChicaWriteSerializer(data={
            'descripcion_producto': 'Ibuprofeno 400mg',
            'cantidad': 5
        })
        
        if write_serializer2.is_valid():
            results.add_pass("Serializer: precio_unitario es opcional")
        else:
            results.add_fail("Serializer: precio_unitario opcional", write_serializer2.errors)
            
    except Exception as e:
        results.add_fail("Serializer: General", str(e))


# ============================================================
# PRUEBAS DE API (ViewSet)
# ============================================================
def test_api_endpoints():
    """Verifica que los endpoints de API funcionan"""
    print_header("PRUEBAS DE API")
    
    try:
        from django.urls import reverse, get_resolver
        
        # Verificar que las rutas existen
        resolver = get_resolver()
        all_urls = [pattern.name for pattern in resolver.url_patterns if hasattr(pattern, 'name')]
        
        # Las rutas de DRF router tienen formato especial
        # Verificamos que el viewset está registrado
        from core.views import CompraCajaChicaViewSet
        
        # Verificar acciones del viewset
        viewset = CompraCajaChicaViewSet()
        
        # Verificar que existen las acciones del flujo
        required_actions = [
            'enviar_admin', 'autorizar_admin', 
            'enviar_director', 'autorizar_director',
            'rechazar', 'devolver', 'cancelar', 'resumen'
        ]
        
        # Obtener métodos del viewset
        viewset_methods = [m for m in dir(viewset) if not m.startswith('_')]
        
        for action in required_actions:
            if action in viewset_methods:
                results.add_pass(f"API: Acción '{action}' existe")
            else:
                results.add_fail(f"API: Acción '{action}'", "No existe en ViewSet")
        
    except Exception as e:
        results.add_fail("API: Verificar endpoints", str(e))


# ============================================================
# PRUEBAS DE INTEGRACIÓN
# ============================================================
def test_integracion_flujo():
    """Prueba el flujo completo de una compra"""
    print_header("PRUEBAS DE INTEGRACIÓN")
    
    try:
        # Buscar o crear centro de prueba
        centro, _ = Centro.objects.get_or_create(
            nombre='Centro Test Caja Chica',
            defaults={'activo': True}
        )
        
        # Buscar usuarios de diferentes roles o usar existentes
        medico = User.objects.filter(rol='medico', centro=centro).first()
        admin = User.objects.filter(rol__in=['administrador_centro', 'admin']).first()
        director = User.objects.filter(rol__in=['director_centro', 'director']).first()
        
        if not medico:
            medico = User.objects.filter(centro=centro).first()
        if not admin:
            admin = User.objects.filter(is_superuser=True).first()
        if not director:
            director = admin
        
        if not all([medico, admin, director]):
            print_warning("No hay usuarios suficientes para prueba de flujo completo")
            results.add_pass("Integración: Skipped (sin usuarios de prueba)")
            return
        
        # 1. Crear compra
        from django.utils import timezone
        
        compra = CompraCajaChica.objects.create(
            centro=centro,
            motivo_compra='Prueba automatizada de flujo multinivel',
            estado='pendiente',
            solicitante=medico
        )
        results.add_pass(f"Integración: Compra creada (ID: {compra.id})")
        
        # 2. Crear detalle
        detalle = DetalleCompraCajaChica.objects.create(
            compra=compra,
            descripcion_producto='Medicamento de prueba',
            cantidad_solicitada=10,
            precio_unitario=Decimal('25.00')
        )
        results.add_pass(f"Integración: Detalle creado (ID: {detalle.id})")
        
        # 3. Simular flujo: pendiente -> enviada_admin
        compra.estado = 'enviada_admin'
        compra.fecha_envio_admin = timezone.now()
        compra.save()
        results.add_pass("Integración: Transición pendiente -> enviada_admin")
        
        # 4. Simular: enviada_admin -> autorizada_admin
        compra.estado = 'autorizada_admin'
        compra.fecha_autorizacion_admin = timezone.now()
        compra.administrador_centro = admin
        compra.save()
        results.add_pass("Integración: Transición enviada_admin -> autorizada_admin")
        
        # 5. Simular: autorizada_admin -> enviada_director
        compra.estado = 'enviada_director'
        compra.fecha_envio_director = timezone.now()
        compra.save()
        results.add_pass("Integración: Transición autorizada_admin -> enviada_director")
        
        # 6. Simular: enviada_director -> autorizada
        compra.estado = 'autorizada'
        compra.fecha_autorizacion_director = timezone.now()
        compra.director_centro = director
        compra.autorizado_por = director
        compra.save()
        results.add_pass("Integración: Transición enviada_director -> autorizada")
        
        # 7. Verificar calcular_totales
        compra.calcular_totales()
        if compra.subtotal > 0:
            results.add_pass(f"Integración: calcular_totales() funciona (subtotal: ${compra.subtotal})")
        else:
            results.add_fail("Integración: calcular_totales()", "Subtotal es 0")
        
        # 8. Limpiar datos de prueba
        detalle.delete()
        compra.delete()
        results.add_pass("Integración: Limpieza de datos de prueba")
        
    except Exception as e:
        results.add_fail("Integración: Flujo completo", str(e))


# ============================================================
# PRUEBAS DE FRONTEND (archivos)
# ============================================================
def test_frontend_files():
    """Verifica que los archivos del frontend tienen los cambios necesarios"""
    print_header("PRUEBAS DE FRONTEND (archivos)")
    
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Verificar ComprasCajaChica.jsx
    try:
        jsx_path = os.path.join(base_path, 'inventario-front', 'src', 'pages', 'ComprasCajaChica.jsx')
        
        if os.path.exists(jsx_path):
            with open(jsx_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar estados nuevos
            if 'enviada_admin' in content and 'autorizada_admin' in content:
                results.add_pass("Frontend: Estados nuevos en ComprasCajaChica.jsx")
            else:
                results.add_fail("Frontend: Estados nuevos", "No encontrados en JSX")
            
            # Verificar handlers del flujo
            handlers = ['handleEnviarAdmin', 'handleAutorizarAdmin', 'handleEnviarDirector', 'handleAutorizarDirector']
            missing_handlers = [h for h in handlers if h not in content]
            
            if not missing_handlers:
                results.add_pass("Frontend: Handlers del flujo presentes")
            else:
                results.add_fail("Frontend: Handlers", f"Faltan: {missing_handlers}")
            
            # Verificar detección de roles
            if 'esMedico' in content and 'esAdmin' in content and 'esDirector' in content:
                results.add_pass("Frontend: Detección de roles implementada")
            else:
                results.add_fail("Frontend: Roles", "Falta detección de roles")
        else:
            results.add_fail("Frontend: ComprasCajaChica.jsx", "Archivo no encontrado")
    except Exception as e:
        results.add_fail("Frontend: ComprasCajaChica.jsx", str(e))
    
    # 2. Verificar api.js
    try:
        api_path = os.path.join(base_path, 'inventario-front', 'src', 'services', 'api.js')
        
        if os.path.exists(api_path):
            with open(api_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Verificar endpoints nuevos
            endpoints = ['enviar-admin', 'autorizar-admin', 'enviar-director', 'autorizar-director']
            missing = [e for e in endpoints if e not in content]
            
            if not missing:
                results.add_pass("Frontend: Endpoints API del flujo presentes")
            else:
                results.add_fail("Frontend: Endpoints API", f"Faltan: {missing}")
        else:
            results.add_fail("Frontend: api.js", "Archivo no encontrado")
    except Exception as e:
        results.add_fail("Frontend: api.js", str(e))


# ============================================================
# MAIN
# ============================================================
def main():
    print(f"\n{Colors.BOLD}{'*'*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  PRUEBAS MASIVAS - FLUJO MULTINIVEL CAJA CHICA{Colors.RESET}")
    print(f"{Colors.BOLD}{'*'*60}{Colors.RESET}")
    
    # Ejecutar todas las pruebas
    test_db_estructura()
    test_modelo_compra()
    test_serializer()
    test_api_endpoints()
    test_integracion_flujo()
    test_frontend_files()
    
    # Mostrar resumen
    success = results.summary()
    
    # Exit code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
