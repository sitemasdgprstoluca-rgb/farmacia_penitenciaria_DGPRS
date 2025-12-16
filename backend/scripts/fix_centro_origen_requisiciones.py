"""
Script para corregir la semántica de centros en requisiciones existentes.

PROBLEMA: Las requisiciones fueron creadas con:
- centro_destino = centro del solicitante (INCORRECTO)
- centro_origen = NULL (INCORRECTO)

CORRECCIÓN: Debe ser:
- centro_origen = centro del solicitante (de donde SALE la requisición)
- centro_destino = NULL (farmacia central, a donde VA)

Este script intercambia los valores para corregir la semántica.
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from core.models import Requisicion


def fix_centro_origen():
    """
    Corrige requisiciones donde:
    - centro_origen IS NULL
    - centro_destino IS NOT NULL
    
    Mueve centro_destino → centro_origen y pone centro_destino = NULL
    """
    print("=" * 60)
    print("CORRECCIÓN DE SEMÁNTICA DE CENTROS EN REQUISICIONES")
    print("=" * 60)
    
    # Buscar requisiciones con la semántica invertida
    requisiciones_incorrectas = Requisicion.objects.filter(
        centro_origen__isnull=True,
        centro_destino__isnull=False
    )
    
    total = requisiciones_incorrectas.count()
    print(f"\nRequisiciones a corregir: {total}")
    
    if total == 0:
        print("No hay requisiciones que corregir.")
        return
    
    # Mostrar preview
    print("\nPreview de cambios:")
    print("-" * 60)
    for req in requisiciones_incorrectas[:10]:  # Mostrar máximo 10
        print(f"  REQ {req.numero} (ID: {req.id})")
        print(f"    ANTES:  centro_origen=NULL, centro_destino={req.centro_destino_id}")
        print(f"    DESPUÉS: centro_origen={req.centro_destino_id}, centro_destino=NULL")
    
    if total > 10:
        print(f"  ... y {total - 10} más")
    
    # Confirmar
    print("\n" + "-" * 60)
    respuesta = input("¿Desea aplicar estos cambios? (s/N): ").strip().lower()
    
    if respuesta != 's':
        print("Operación cancelada.")
        return
    
    # Aplicar corrección
    print("\nAplicando corrección...")
    
    with transaction.atomic():
        corregidas = 0
        errores = 0
        
        for req in requisiciones_incorrectas:
            try:
                # Guardar el valor actual de centro_destino
                centro_solicitante = req.centro_destino_id
                
                # Intercambiar: centro_destino → centro_origen
                req.centro_origen_id = centro_solicitante
                req.centro_destino_id = None  # Farmacia central no tiene centro
                
                req.save(update_fields=['centro_origen_id', 'centro_destino_id'])
                corregidas += 1
                
                print(f"  ✓ REQ {req.numero}: centro_origen={centro_solicitante}, centro_destino=NULL")
                
            except Exception as e:
                errores += 1
                print(f"  ✗ REQ {req.numero}: Error - {e}")
    
    print("\n" + "=" * 60)
    print(f"RESULTADO: {corregidas} corregidas, {errores} errores")
    print("=" * 60)


def verificar_estado():
    """Muestra el estado actual de las requisiciones."""
    print("\nESTADO ACTUAL DE REQUISICIONES:")
    print("-" * 60)
    
    total = Requisicion.objects.count()
    con_origen = Requisicion.objects.filter(centro_origen__isnull=False).count()
    sin_origen = Requisicion.objects.filter(centro_origen__isnull=True).count()
    con_destino = Requisicion.objects.filter(centro_destino__isnull=False).count()
    sin_destino = Requisicion.objects.filter(centro_destino__isnull=True).count()
    
    # Casos problemáticos
    invertidas = Requisicion.objects.filter(
        centro_origen__isnull=True,
        centro_destino__isnull=False
    ).count()
    
    print(f"  Total requisiciones: {total}")
    print(f"  Con centro_origen: {con_origen}")
    print(f"  Sin centro_origen (NULL): {sin_origen}")
    print(f"  Con centro_destino: {con_destino}")
    print(f"  Sin centro_destino (NULL): {sin_destino}")
    print(f"\n  ⚠️  Con semántica invertida (a corregir): {invertidas}")
    
    # Mostrar detalle de las que tienen semántica correcta/incorrecta
    print("\nDETALLE:")
    for req in Requisicion.objects.all()[:20]:
        estado = "✓" if req.centro_origen_id else "✗"
        print(f"  {estado} {req.numero}: origen={req.centro_origen_id}, destino={req.centro_destino_id}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Corrige semántica de centros en requisiciones')
    parser.add_argument('--verificar', '-v', action='store_true', 
                       help='Solo verificar estado, no corregir')
    parser.add_argument('--auto', '-y', action='store_true',
                       help='Aplicar corrección sin confirmación')
    
    args = parser.parse_args()
    
    if args.verificar:
        verificar_estado()
    else:
        if args.auto:
            # Modo automático sin confirmación (para producción)
            from django.db import transaction
            
            requisiciones_incorrectas = Requisicion.objects.filter(
                centro_origen__isnull=True,
                centro_destino__isnull=False
            )
            
            total = requisiciones_incorrectas.count()
            print(f"Corrigiendo {total} requisiciones...")
            
            with transaction.atomic():
                for req in requisiciones_incorrectas:
                    centro_solicitante = req.centro_destino_id
                    req.centro_origen_id = centro_solicitante
                    req.centro_destino_id = None
                    req.save(update_fields=['centro_origen_id', 'centro_destino_id'])
                    print(f"  ✓ {req.numero}")
            
            print(f"Completado: {total} requisiciones corregidas")
        else:
            fix_centro_origen()
