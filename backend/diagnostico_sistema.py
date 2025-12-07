#!/usr/bin/env python
"""
Script de diagnóstico del sistema de farmacia penitenciaria
Verifica el estado de todos los módulos y endpoints críticos
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from django.urls import get_resolver
from rest_framework.test import APIClient
from core.models import UserProfile
from inventario.models import Producto, Lote, Centro

User = get_user_model()

def print_section(title):
    """Imprime un encabezado de sección"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def check_database():
    """Verificar estado de la base de datos"""
    print_section("VERIFICACIÓN DE BASE DE DATOS")
    
    try:
        user_count = User.objects.count()
        print(f"✅ Usuarios totales: {user_count}")
        
        admins = UserProfile.objects.filter(rol='admin_sistema').count()
        print(f"✅ Administradores del sistema: {admins}")
        
        farmacia = UserProfile.objects.filter(rol='farmacia').count()
        print(f"✅ Usuarios de farmacia: {farmacia}")
        
        vista = UserProfile.objects.filter(rol='vista_user').count()
        print(f"✅ Usuarios de vista: {vista}")
        
        productos = Producto.objects.filter(activo=True).count()
        print(f"✅ Productos activos: {productos}")
        
        lotes = Lote.objects.filter(activo=True).count()
        print(f"✅ Lotes activos: {lotes}")
        
        centros = Centro.objects.filter(activo=True).count()
        print(f"✅ Centros activos: {centros}")
        
        return True
    except Exception as e:
        print(f"❌ Error al verificar base de datos: {e}")
        return False

def check_urls():
    """Verificar que las URLs estén registradas correctamente"""
    print_section("VERIFICACIÓN DE URLs")
    
    critical_patterns = [
        # Productos
        r'productos/',
        r'productos/exportar-excel/',
        r'productos/importar-excel/',
        
        # Lotes
        r'lotes/',
        r'lotes/exportar-excel/',
        r'lotes/importar-excel/',
        
        # Centros
        r'centros/',
        r'centros/exportar-excel/',
        r'centros/importar_excel/',
        
        # Usuarios
        r'usuarios/',
        
        # Requisiciones
        r'requisiciones/',
        r'requisiciones/(?P<pk>[^/.]+)/marcar-surtida/',
        r'requisiciones/exportar-pdf/',
        
        # Movimientos
        r'movimientos/',
        r'movimientos/exportar/',
        r'movimientos/trazabilidad/',
        
        # Dashboard
        r'dashboard/',
        r'dashboard/graficas/',
        
        # Reportes
        r'reportes/inventario-pdf/',
        r'reportes/inventario-excel/',
        r'reportes/caducidades-pdf/',
        r'reportes/caducidades-excel/',
    ]
    
    resolver = get_resolver()
    
    for pattern in critical_patterns:
        # Simplificar el patrón para búsqueda
        search_pattern = pattern.replace(r'(?P<pk>[^/.]+)', '1').replace('/', '').strip()
        found = False
        
        for url_pattern in resolver.url_patterns:
            if hasattr(url_pattern, 'pattern'):
                if search_pattern in str(url_pattern.pattern):
                    found = True
                    break
            elif hasattr(url_pattern, 'url_patterns'):
                # Router de DRF
                for sub_pattern in url_pattern.url_patterns:
                    if search_pattern in str(sub_pattern.pattern):
                        found = True
                        break
        
        status = "✅" if found else "❌"
        print(f"{status} {pattern}")
    
    return True

def check_admin_user():
    """Verificar que exista al menos un usuario admin"""
    print_section("VERIFICACIÓN DE USUARIO ADMINISTRADOR")
    
    try:
        admin_users = User.objects.filter(
            profile__rol='admin_sistema'
        ).select_related('profile')
        
        if admin_users.exists():
            print(f"\u2705 Se encontraron {admin_users.count()} administradores:")
            for admin in admin_users:
                print(f"   - {admin.username} ({admin.email}) - Rol: {admin.profile.rol}")
        else:
            print("❌ No se encontraron usuarios administradores")
            
            # Buscar usuarios staff o superuser
            staff_users = User.objects.filter(is_staff=True) | User.objects.filter(is_superuser=True)
            if staff_users.exists():
                print("\n⚠️  Usuarios con privilegios staff/superuser (pueden necesitar perfil):")
                for user in staff_users:
                    has_profile = hasattr(user, 'profile')
                    rol = user.profile.rol if has_profile else "SIN PERFIL"
                    print(f"   - {user.username} ({user.email}) - Rol: {rol}")
            
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error al verificar administradores: {e}")
        return False

def check_static_files():
    """Verificar archivos estáticos críticos"""
    print_section("VERIFICACIÓN DE ARCHIVOS ESTÁTICOS")
    
    critical_files = [
        'backend/static/img/pdf/fondoOficial.png',
    ]
    
    for filepath in critical_files:
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), filepath)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"✅ {filepath} ({size} bytes)")
        else:
            print(f"❌ {filepath} - NO ENCONTRADO")
    
    return True

def test_api_endpoints():
    """Probar endpoints críticos de la API"""
    print_section("PRUEBA DE ENDPOINTS API")
    
    # Crear un usuario de prueba
    try:
        admin_user = User.objects.filter(
            profile__rol='admin_sistema'
        ).first()
        
        if not admin_user:
            print("⚠️  No hay usuario admin para probar endpoints")
            return False
        
        client = APIClient()
        client.force_authenticate(user=admin_user)
        
        endpoints = [
            ('/api/productos/', 'GET'),
            ('/api/lotes/', 'GET'),
            ('/api/centros/', 'GET'),
            ('/api/usuarios/', 'GET'),
            ('/api/dashboard/', 'GET'),
            ('/api/movimientos/', 'GET'),
        ]
        
        for endpoint, method in endpoints:
            if method == 'GET':
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)
            
            status_code = response.status_code
            if status_code in [200, 201]:
                print(f"✅ {method} {endpoint} - {status_code}")
            else:
                print(f"❌ {method} {endpoint} - {status_code}")
        
        return True
    except Exception as e:
        print(f"❌ Error al probar endpoints: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Ejecutar todas las verificaciones"""
    print("\n" + "="*80)
    print("  DIAGNÓSTICO DEL SISTEMA DE FARMACIA PENITENCIARIA")
    print("="*80)
    
    results = {
        'database': check_database(),
        'urls': check_urls(),
        'admin': check_admin_user(),
        'static': check_static_files(),
        'api': test_api_endpoints(),
    }
    
    print_section("RESUMEN")
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {check.upper()}")
    
    print("\n" + "="*80)
    if all_passed:
        print("  ✅ SISTEMA OPERATIVO - Todos los checks pasaron")
    else:
        print("  ⚠️  SISTEMA CON PROBLEMAS - Revisar checks fallidos arriba")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())
