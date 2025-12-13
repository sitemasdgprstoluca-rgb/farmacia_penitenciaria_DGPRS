"""
Script de sanitización de permisos para usuarios de Centro.

Este script corrige la desalineación entre los permisos almacenados en BD y los
permisos esperados según el rol. Específicamente, establece perm_reportes y
perm_trazabilidad en False para todos los roles de Centro.

Ejecutar con: python manage.py shell < scripts/sanitize_centro_permissions.py
O bien: python manage.py runscript sanitize_centro_permissions

ISS-FIX: Resuelve el bug donde administrador_centro y director_centro recibían
permisos de Reportes/Trazabilidad indebidamente.
"""
import os
import sys
import django

# Configurar Django si se ejecuta standalone
if __name__ == '__main__':
    # Asegurar que estamos en el directorio correcto
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, backend_dir)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from django.db import transaction
from core.models import User


# Roles de Centro que NO deben tener permisos de reportes/trazabilidad
ROLES_CENTRO = [
    'medico',
    'administrador_centro',
    'director_centro',
    'centro',
    'usuario_centro',
    'usuario_normal',
]


def sanitize_centro_permissions(dry_run=True):
    """
    Sanitiza los permisos de usuarios de Centro.
    
    Args:
        dry_run: Si True, solo muestra qué cambios se harían sin aplicarlos.
        
    Returns:
        dict: Resumen de usuarios afectados.
    """
    results = {
        'checked': 0,
        'fixed_reportes': [],
        'fixed_trazabilidad': [],
        'errors': [],
    }
    
    print(f"\n{'='*60}")
    print(f"SANITIZACIÓN DE PERMISOS DE CENTRO")
    print(f"{'='*60}")
    print(f"Modo: {'DRY RUN (simulación)' if dry_run else 'EJECUCIÓN REAL'}")
    print(f"Roles a verificar: {', '.join(ROLES_CENTRO)}")
    print(f"{'='*60}\n")
    
    try:
        # Obtener usuarios de roles de Centro con permisos incorrectos
        usuarios_con_reportes = User.objects.filter(
            rol__in=ROLES_CENTRO,
            perm_reportes=True
        )
        
        usuarios_con_trazabilidad = User.objects.filter(
            rol__in=ROLES_CENTRO,
            perm_trazabilidad=True
        )
        
        results['checked'] = User.objects.filter(rol__in=ROLES_CENTRO).count()
        
        print(f"Usuarios de Centro verificados: {results['checked']}")
        print(f"Usuarios con perm_reportes=True (incorrecto): {usuarios_con_reportes.count()}")
        print(f"Usuarios con perm_trazabilidad=True (incorrecto): {usuarios_con_trazabilidad.count()}")
        print()
        
        # Procesar usuarios con perm_reportes incorrecto
        if usuarios_con_reportes.exists():
            print("Usuarios con perm_reportes=True:")
            for user in usuarios_con_reportes:
                print(f"  - {user.username} (ID: {user.id}, rol: {user.rol})")
                results['fixed_reportes'].append({
                    'id': user.id,
                    'username': user.username,
                    'rol': user.rol,
                })
        
        # Procesar usuarios con perm_trazabilidad incorrecto
        if usuarios_con_trazabilidad.exists():
            print("\nUsuarios con perm_trazabilidad=True:")
            for user in usuarios_con_trazabilidad:
                print(f"  - {user.username} (ID: {user.id}, rol: {user.rol})")
                results['fixed_trazabilidad'].append({
                    'id': user.id,
                    'username': user.username,
                    'rol': user.rol,
                })
        
        # Aplicar correcciones si no es dry_run
        if not dry_run:
            with transaction.atomic():
                # Corregir perm_reportes
                count_reportes = usuarios_con_reportes.update(perm_reportes=False)
                # Corregir perm_trazabilidad
                count_trazabilidad = usuarios_con_trazabilidad.update(perm_trazabilidad=False)
                
                print(f"\n{'='*60}")
                print("CORRECCIONES APLICADAS:")
                print(f"  - perm_reportes -> False: {count_reportes} usuarios")
                print(f"  - perm_trazabilidad -> False: {count_trazabilidad} usuarios")
                print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print("DRY RUN COMPLETADO - No se aplicaron cambios")
            print("Ejecutar con dry_run=False para aplicar correcciones")
            print(f"{'='*60}")
            
    except Exception as e:
        results['errors'].append(str(e))
        print(f"\nERROR: {e}")
        
    return results


def verify_permissions():
    """
    Verifica que los permisos estén correctamente configurados después de sanitizar.
    
    Returns:
        bool: True si todos los permisos son correctos.
    """
    print(f"\n{'='*60}")
    print("VERIFICACIÓN POST-SANITIZACIÓN")
    print(f"{'='*60}\n")
    
    # Verificar que no queden usuarios de Centro con permisos incorrectos
    usuarios_incorrectos = User.objects.filter(
        rol__in=ROLES_CENTRO
    ).filter(
        perm_reportes=True
    ) | User.objects.filter(
        rol__in=ROLES_CENTRO
    ).filter(
        perm_trazabilidad=True
    )
    
    if usuarios_incorrectos.exists():
        print("❌ VERIFICACIÓN FALLIDA")
        print(f"   Aún hay {usuarios_incorrectos.count()} usuarios con permisos incorrectos")
        for user in usuarios_incorrectos:
            print(f"   - {user.username}: reportes={user.perm_reportes}, trazabilidad={user.perm_trazabilidad}")
        return False
    else:
        print("✅ VERIFICACIÓN EXITOSA")
        print("   Todos los usuarios de Centro tienen permisos correctos")
        return True


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Sanitizar permisos de usuarios de Centro')
    parser.add_argument('--execute', action='store_true', 
                        help='Ejecutar cambios (default: dry run)')
    parser.add_argument('--verify-only', action='store_true',
                        help='Solo verificar sin hacer cambios')
    
    args = parser.parse_args()
    
    if args.verify_only:
        verify_permissions()
    else:
        sanitize_centro_permissions(dry_run=not args.execute)
        if args.execute:
            verify_permissions()
