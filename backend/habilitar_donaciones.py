#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para habilitar el módulo de donaciones para usuarios ADMIN y FARMACIA
"""
import django
import os
import sys

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def habilitar_donaciones():
    """Habilitar permiso de donaciones para usuarios ADMIN y FARMACIA"""
    print("=" * 70)
    print("HABILITANDO MÓDULO DE DONACIONES")
    print("=" * 70)
    
    # Buscar usuarios ADMIN y FARMACIA sin permiso de donaciones
    usuarios_objetivo = User.objects.filter(
        rol__in=['ADMIN', 'FARMACIA'],
        is_active=True
    )
    
    if not usuarios_objetivo.exists():
        print("\n⚠️  No se encontraron usuarios ADMIN o FARMACIA activos")
        return
    
    print(f"\nUsuarios encontrados: {usuarios_objetivo.count()}")
    
    actualizados = 0
    ya_tenian = 0
    
    for user in usuarios_objetivo:
        perm_actual = getattr(user, 'perm_donaciones', None)
        
        if perm_actual is None or perm_actual is False:
            user.perm_donaciones = True
            user.save()
            print(f"✅ {user.username} ({user.rol}) - Permiso habilitado")
            actualizados += 1
        else:
            print(f"ℹ️  {user.username} ({user.rol}) - Ya tenía el permiso")
            ya_tenian += 1
    
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Usuarios actualizados: {actualizados}")
    print(f"Usuarios que ya tenían permiso: {ya_tenian}")
    
    if actualizados > 0:
        print("\n✅ Módulo de donaciones habilitado exitosamente")
        print("\n📝 Próximos pasos:")
        print("   1. Cierra sesión en el frontend")
        print("   2. Vuelve a iniciar sesión")
        print("   3. Limpia el caché del navegador (Ctrl+Shift+R)")
        print("   4. El módulo 'Donaciones' debería aparecer en el menú lateral")
    else:
        print("\n✅ Todos los usuarios ya tenían el permiso configurado")
        print("\n📝 Si aún no ves el módulo:")
        print("   1. Verifica que tu usuario tiene rol ADMIN o FARMACIA")
        print("   2. Cierra sesión y vuelve a iniciar sesión")
        print("   3. Limpia el caché del navegador (Ctrl+Shift+R)")
        print("   4. Revisa la consola del navegador (F12) en busca de errores")

if __name__ == '__main__':
    print("\n🔧 CONFIGURACIÓN DEL MÓDULO DE DONACIONES\n")
    habilitar_donaciones()
    print()
