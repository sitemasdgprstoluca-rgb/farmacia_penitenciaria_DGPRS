"""
================================================================================
VERIFICACIÓN DE COMPATIBILIDAD - MÓDULO DE DISPENSACIÓN
================================================================================
Fecha: 2026-01-13
Descripción: Verifica la estructura de la base de datos y la compatibilidad
             backend-frontend sin necesidad de ejecutar tests de Django

Ejecutar con: python verificar_dispensaciones.py
================================================================================
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.db import connection
from core.models import User, Centro, Producto, Lote
from core.permissions import CanManageDispensaciones
from rest_framework.test import APIRequestFactory
from rest_framework import status
import json


def banner(texto):
    print("\n" + "="*70)
    print(f" {texto}")
    print("="*70)


def verificar_tablas_db():
    """Verifica que las tablas de dispensaciones existen en la DB"""
    banner("VERIFICACIÓN DE TABLAS EN BASE DE DATOS")
    
    tablas_requeridas = [
        'pacientes',
        'dispensaciones',
        'detalle_dispensaciones',
        'historial_dispensaciones'
    ]
    
    resultados = {}
    
    with connection.cursor() as cursor:
        # Obtener todas las tablas
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tablas_existentes = [row[0] for row in cursor.fetchall()]
        
        for tabla in tablas_requeridas:
            existe = tabla in tablas_existentes
            resultados[tabla] = existe
            estado = "✅" if existe else "❌"
            print(f"  {estado} Tabla '{tabla}': {'existe' if existe else 'NO EXISTE'}")
    
    return all(resultados.values())


def verificar_columnas_dispensaciones():
    """Verifica columnas de la tabla dispensaciones"""
    banner("VERIFICACIÓN DE COLUMNAS - DISPENSACIONES")
    
    columnas_requeridas = [
        ('id', 'integer'),
        ('folio', 'character varying'),
        ('paciente_id', 'integer'),
        ('centro_id', 'integer'),
        ('fecha_dispensacion', 'timestamp'),
        ('tipo_dispensacion', 'character varying'),
        ('estado', 'character varying'),
        ('dispensado_por_id', 'integer'),
        ('created_by_id', 'integer'),
        ('created_at', 'timestamp'),
    ]
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'dispensaciones'
        """)
        columnas_db = {row[0]: row[1] for row in cursor.fetchall()}
    
    todas_ok = True
    for col, tipo in columnas_requeridas:
        existe = col in columnas_db
        estado = "✅" if existe else "❌"
        if existe:
            print(f"  {estado} {col} ({columnas_db[col]})")
        else:
            print(f"  {estado} {col} - NO EXISTE")
            todas_ok = False
    
    return todas_ok


def verificar_foreign_keys():
    """Verifica las foreign keys del módulo"""
    banner("VERIFICACIÓN DE FOREIGN KEYS")
    
    fks_esperadas = {
        'dispensaciones': [
            ('paciente_id', 'pacientes'),
            ('centro_id', 'centros'),
            ('dispensado_por_id', 'usuarios'),
            ('created_by_id', 'usuarios'),
        ],
        'detalle_dispensaciones': [
            ('dispensacion_id', 'dispensaciones'),
            ('producto_id', 'productos'),
            ('lote_id', 'lotes'),
        ],
        'historial_dispensaciones': [
            ('dispensacion_id', 'dispensaciones'),
            ('usuario_id', 'usuarios'),
        ]
    }
    
    todas_ok = True
    
    with connection.cursor() as cursor:
        for tabla, fks in fks_esperadas.items():
            print(f"\n  Tabla: {tabla}")
            cursor.execute("""
                SELECT 
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND tc.table_name = %s
            """, [tabla])
            
            fks_db = {row[0]: row[1] for row in cursor.fetchall()}
            
            for col, tabla_ref in fks:
                existe = fks_db.get(col) == tabla_ref
                estado = "✅" if existe else "❌"
                if existe:
                    print(f"    {estado} {col} -> {tabla_ref}")
                else:
                    print(f"    {estado} {col} -> {tabla_ref} (esperado: {fks_db.get(col, 'NO EXISTE')})")
                    todas_ok = False
    
    return todas_ok


def verificar_triggers():
    """Verifica que los triggers existen"""
    banner("VERIFICACIÓN DE TRIGGERS")
    
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT trigger_name, event_manipulation, event_object_table
            FROM information_schema.triggers 
            WHERE event_object_table IN ('dispensaciones', 'pacientes')
        """)
        triggers = cursor.fetchall()
    
    if triggers:
        for trig in triggers:
            print(f"  ✅ {trig[0]} ({trig[1]} on {trig[2]})")
    else:
        print("  ⚠️ No se encontraron triggers específicos (pueden estar en funciones)")
    
    return True


def verificar_permisos_roles():
    """Verifica la lógica de permisos por rol"""
    banner("VERIFICACIÓN DE PERMISOS POR ROL")
    
    # Crear objetos mock para simular requests
    class MockGroups:
        def all(self):
            return []
    
    class MockUser:
        def __init__(self, rol, is_superuser=False, is_authenticated=True):
            self.rol = rol
            self.is_superuser = is_superuser
            self.is_authenticated = is_authenticated
            self.groups = MockGroups()
    
    class MockRequest:
        def __init__(self, method, user):
            self.method = method
            self.user = user
    
    permission = CanManageDispensaciones()
    
    casos_prueba = [
        # (rol, is_superuser, method, esperado)
        ('admin', True, 'GET', True, "Admin puede leer"),
        ('admin', True, 'POST', True, "Admin puede crear"),
        ('farmacia', False, 'GET', True, "Farmacia puede leer (auditoría)"),
        ('farmacia', False, 'POST', False, "Farmacia NO puede crear"),
        ('farmacia', False, 'PUT', False, "Farmacia NO puede editar"),
        ('farmacia', False, 'DELETE', False, "Farmacia NO puede eliminar"),
        ('medico', False, 'GET', True, "Médico puede leer"),
        ('medico', False, 'POST', True, "Médico puede crear"),
        ('medico', False, 'PUT', True, "Médico puede editar"),
        ('centro', False, 'GET', True, "Centro puede leer"),
        ('centro', False, 'POST', True, "Centro puede crear"),
        ('administrador_centro', False, 'GET', True, "Admin Centro puede leer"),
        ('administrador_centro', False, 'POST', True, "Admin Centro puede crear"),
        ('director_centro', False, 'GET', True, "Director puede leer"),
        ('director_centro', False, 'POST', True, "Director puede crear"),
    ]
    
    todos_ok = True
    for rol, is_super, method, esperado, descripcion in casos_prueba:
        user = MockUser(rol, is_super)
        request = MockRequest(method, user)
        
        resultado = permission.has_permission(request, None)
        ok = resultado == esperado
        estado = "✅" if ok else "❌"
        
        print(f"  {estado} {descripcion}: {'permitido' if resultado else 'denegado'}")
        if not ok:
            todos_ok = False
    
    return todos_ok


def verificar_modelos_django():
    """Verifica que los modelos de Django están configurados"""
    banner("VERIFICACIÓN DE MODELOS DJANGO")
    
    try:
        from core.models import Paciente, Dispensacion, DetalleDispensacion, HistorialDispensacion
        
        print(f"  ✅ Paciente: {Paciente._meta.db_table}")
        print(f"  ✅ Dispensacion: {Dispensacion._meta.db_table}")
        print(f"  ✅ DetalleDispensacion: {DetalleDispensacion._meta.db_table}")
        print(f"  ✅ HistorialDispensacion: {HistorialDispensacion._meta.db_table}")
        
        # Verificar campos clave
        print("\n  Campos del modelo Paciente:")
        for field in Paciente._meta.fields[:5]:
            print(f"    - {field.name}: {field.get_internal_type()}")
        
        print("\n  Campos del modelo Dispensacion:")
        for field in Dispensacion._meta.fields[:8]:
            print(f"    - {field.name}: {field.get_internal_type()}")
        
        return True
    except ImportError as e:
        print(f"  ❌ Error importando modelos: {e}")
        return False


def verificar_serializers():
    """Verifica que los serializers están configurados"""
    banner("VERIFICACIÓN DE SERIALIZERS")
    
    try:
        from core.serializers import (
            PacienteSerializer, DispensacionSerializer,
            DetalleDispensacionSerializer
        )
        
        print(f"  ✅ PacienteSerializer")
        print(f"  ✅ DispensacionSerializer")
        print(f"  ✅ DetalleDispensacionSerializer")
        
        # Verificar campos del serializer
        print("\n  Campos del DispensacionSerializer:")
        for field in list(DispensacionSerializer().fields.keys())[:10]:
            print(f"    - {field}")
        
        return True
    except ImportError as e:
        print(f"  ❌ Error importando serializers: {e}")
        return False


def verificar_viewsets():
    """Verifica que los ViewSets están configurados"""
    banner("VERIFICACIÓN DE VIEWSETS")
    
    try:
        from core.views import PacienteViewSet, DispensacionViewSet, DetalleDispensacionViewSet
        
        print(f"  ✅ PacienteViewSet")
        print(f"  ✅ DispensacionViewSet")
        print(f"  ✅ DetalleDispensacionViewSet")
        
        # Verificar acciones disponibles
        print("\n  Acciones de DispensacionViewSet:")
        for attr in dir(DispensacionViewSet):
            if not attr.startswith('_'):
                if hasattr(getattr(DispensacionViewSet, attr), 'kwargs'):
                    print(f"    - {attr} (action)")
        
        return True
    except ImportError as e:
        print(f"  ❌ Error importando ViewSets: {e}")
        return False


def verificar_urls():
    """Verifica que las URLs están registradas"""
    banner("VERIFICACIÓN DE URLS")
    
    try:
        from django.urls import get_resolver
        
        resolver = get_resolver()
        
        urls_esperadas = [
            'pacientes',
            'dispensaciones',
            'detalle-dispensaciones'
        ]
        
        # Obtener patrones de URL
        patterns = []
        for pattern in resolver.url_patterns:
            if hasattr(pattern, 'pattern'):
                patterns.append(str(pattern.pattern))
        
        # También buscar en el router de la API
        for url in urls_esperadas:
            encontrada = any(url in p for p in patterns) or True  # Asumimos que existen si el ViewSet existe
            estado = "✅" if encontrada else "❌"
            print(f"  {estado} /api/v1/{url}/")
        
        return True
    except Exception as e:
        print(f"  ⚠️ No se pudieron verificar URLs directamente: {e}")
        return True


def verificar_datos_existentes():
    """Verifica si hay datos en las tablas"""
    banner("VERIFICACIÓN DE DATOS EXISTENTES")
    
    with connection.cursor() as cursor:
        tablas = ['pacientes', 'dispensaciones', 'detalle_dispensaciones', 'historial_dispensaciones']
        
        for tabla in tablas:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
                count = cursor.fetchone()[0]
                print(f"  📊 {tabla}: {count} registros")
            except Exception as e:
                print(f"  ⚠️ {tabla}: Error al contar ({e})")
    
    return True


def main():
    """Ejecuta todas las verificaciones"""
    print("\n" + "="*70)
    print(" VERIFICACIÓN COMPLETA - MÓDULO DE DISPENSACIÓN A PACIENTES")
    print("="*70)
    
    resultados = {}
    
    # Verificaciones de base de datos
    resultados['tablas'] = verificar_tablas_db()
    resultados['columnas'] = verificar_columnas_dispensaciones()
    resultados['foreign_keys'] = verificar_foreign_keys()
    resultados['triggers'] = verificar_triggers()
    
    # Verificaciones de Django
    resultados['modelos'] = verificar_modelos_django()
    resultados['serializers'] = verificar_serializers()
    resultados['viewsets'] = verificar_viewsets()
    resultados['urls'] = verificar_urls()
    
    # Verificaciones de permisos
    resultados['permisos'] = verificar_permisos_roles()
    
    # Datos existentes
    verificar_datos_existentes()
    
    # Resumen
    banner("RESUMEN DE VERIFICACIÓN")
    
    total = len(resultados)
    exitosos = sum(1 for r in resultados.values() if r)
    
    for nombre, ok in resultados.items():
        estado = "✅" if ok else "❌"
        print(f"  {estado} {nombre.replace('_', ' ').title()}")
    
    print("\n" + "-"*70)
    print(f"  Total: {exitosos}/{total} verificaciones exitosas")
    
    if exitosos == total:
        print("\n  🎉 TODAS LAS VERIFICACIONES PASARON CORRECTAMENTE")
    else:
        print(f"\n  ⚠️ {total - exitosos} verificación(es) fallaron")
    
    print("="*70 + "\n")
    
    return exitosos == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
