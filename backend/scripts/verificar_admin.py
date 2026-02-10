#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar configuración de usuario administrador
y permisos de donaciones en producción.
"""
import django
import os
import sys

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Centro

User = get_user_model()

def verificar_admin():
    """Verificar configuración del usuario administrador"""
    print("=" * 70)
    print("VERIFICACIÓN DE USUARIO ADMINISTRADOR")
    print("=" * 70)
    
    # Buscar usuario admin
    try:
        admin = User.objects.filter(rol='ADMIN').first()
        if not admin:
            print("\n❌ ERROR: No hay usuario con rol ADMIN en la base de datos")
            print("\n📝 Para crear un administrador, ejecuta:")
            print("   python manage.py createsuperuser")
            return False
        
        print(f"\n✅ Usuario administrador encontrado:")
        print(f"   Username: {admin.username}")
        print(f"   Email: {admin.email}")
        print(f"   Rol: {admin.rol}")
        print(f"   Activo: {'✅ Sí' if admin.is_active else '❌ NO'}")
        print(f"   Staff: {'✅ Sí' if admin.is_staff else '❌ NO'}")
        print(f"   Superuser: {'✅ Sí' if admin.is_superuser else '❌ NO'}")
        
        # Verificar permisos
        print(f"\n📋 Permisos del usuario:")
        print(f"   perm_donaciones: {getattr(admin, 'perm_donaciones', 'NO DEFINIDO')}")
        print(f"   perm_requisiciones: {getattr(admin, 'perm_requisiciones', 'NO DEFINIDO')}")
        print(f"   perm_movimientos: {getattr(admin, 'perm_movimientos', 'NO DEFINIDO')}")
        print(f"   perm_productos: {getattr(admin, 'perm_productos', 'NO DEFINIDO')}")
        print(f"   perm_lotes: {getattr(admin, 'perm_lotes', 'NO DEFINIDO')}")
        print(f"   perm_notificaciones: {getattr(admin, 'perm_notificaciones', 'NO DEFINIDO')}")
        
        # Verificar centro asignado
        if admin.centro:
            print(f"\n🏢 Centro asignado: {admin.centro.nombre}")
        else:
            print("\n⚠️  ADVERTENCIA: Usuario no tiene centro asignado")
            print("   Esto puede causar problemas en algunas funcionalidades")
        
        # Verificar que puede hacer login
        if not admin.is_active:
            print("\n❌ ERROR CRÍTICO: Usuario está DESACTIVADO")
            print("   No podrá hacer login hasta que se active")
            return False
        
        print("\n✅ Usuario configurado correctamente para producción")
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

def listar_todos_usuarios():
    """Listar todos los usuarios del sistema"""
    print("\n" + "=" * 70)
    print("TODOS LOS USUARIOS EN EL SISTEMA")
    print("=" * 70)
    
    usuarios = User.objects.all().order_by('-is_superuser', 'rol', 'username')
    
    if not usuarios.exists():
        print("\n⚠️  No hay usuarios en el sistema")
        return
    
    print(f"\nTotal: {usuarios.count()} usuarios\n")
    print(f"{'ID':<5} {'Username':<20} {'Rol':<25} {'Activo':<8} {'Donaciones':<12}")
    print("-" * 70)
    
    for user in usuarios:
        activo = "✅" if user.is_active else "❌"
        tiene_donaciones = "✅ Sí" if getattr(user, 'perm_donaciones', None) else "❌ No"
        print(f"{user.id:<5} {user.username:<20} {user.rol:<25} {activo:<8} {tiene_donaciones:<12}")

def verificar_centros():
    """Verificar que existen centros en el sistema"""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE CENTROS")
    print("=" * 70)
    
    centros = Centro.objects.filter(activo=True).count()
    print(f"\nCentros activos: {centros}")
    
    if centros == 0:
        print("\n⚠️  ADVERTENCIA: No hay centros activos en el sistema")
        print("   Esto puede causar problemas en requisiciones y donaciones")

def main():
    print("\n🔍 DIAGNÓSTICO DEL SISTEMA - PRODUCCIÓN\n")
    
    verificar_admin()
    listar_todos_usuarios()
    verificar_centros()
    
    print("\n" + "=" * 70)
    print("RECOMENDACIONES")
    print("=" * 70)
    print("""
1. Si no puedes hacer login:
   - Verifica que el usuario está activo
   - Verifica que la contraseña es correcta
   - Revisa los logs del servidor

2. Si no ves el módulo de Donaciones:
   - Verifica que tu usuario tiene rol ADMIN o FARMACIA
   - Verifica que perm_donaciones no es NULL
   - Limpia el cache del navegador (Ctrl+Shift+R)

3. Para activar un usuario desactivado:
   python backend/manage.py shell
   >>> from django.contrib.auth import get_user_model
   >>> User = get_user_model()
   >>> user = User.objects.get(username='admin')
   >>> user.is_active = True
   >>> user.save()

4. Para habilitar donaciones a un usuario:
   python backend/manage.py shell
   >>> from django.contrib.auth import get_user_model
   >>> User = get_user_model()
   >>> user = User.objects.get(username='admin')
   >>> user.perm_donaciones = True
   >>> user.save()
""")
    
    print("\n✅ Diagnóstico completado\n")

if __name__ == '__main__':
    main()
