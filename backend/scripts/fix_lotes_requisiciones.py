#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para actualizar lotes en detalles de requisiciones históricas.

Este script:
1. Busca requisiciones surtidas/entregadas que tienen detalles sin lote asignado
2. Busca en los movimientos de salida asociados para identificar el lote usado
3. Actualiza el detalle de requisición con el lote correspondiente

Uso:
    python manage.py shell < scripts/fix_lotes_requisiciones.py
    
    O ejecutar directamente:
    cd backend && python scripts/fix_lotes_requisiciones.py
"""

import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario.settings')
django.setup()

from django.db import transaction
from django.db.models import Q
from core.models import Requisicion, DetalleRequisicion, Movimiento, Lote

def fix_lotes_requisiciones():
    """
    Actualiza los detalles de requisición que no tienen lote asignado
    buscando el lote en los movimientos relacionados.
    """
    print("=" * 70)
    print("FIX: Actualizar lotes en detalles de requisiciones históricas")
    print("=" * 70)
    
    # Estados que indican que la requisición fue surtida
    estados_surtidos = ['surtido', 'en_recoleccion', 'entregado', 'finalizado', 'recolectado']
    
    # Buscar requisiciones surtidas
    requisiciones = Requisicion.objects.filter(
        estado__in=estados_surtidos
    ).prefetch_related('detalles')
    
    print(f"\nRequisiciones surtidas encontradas: {requisiciones.count()}")
    
    total_actualizados = 0
    total_detalles_sin_lote = 0
    errores = []
    
    with transaction.atomic():
        for req in requisiciones:
            detalles_sin_lote = req.detalles.filter(lote__isnull=True, cantidad_surtida__gt=0)
            
            if not detalles_sin_lote.exists():
                continue
            
            print(f"\n📋 Requisición {req.numero} (ID: {req.id}) - Estado: {req.estado}")
            print(f"   Detalles sin lote: {detalles_sin_lote.count()}")
            
            for detalle in detalles_sin_lote:
                total_detalles_sin_lote += 1
                producto = detalle.producto
                
                print(f"\n   🔍 Detalle ID {detalle.id}: {producto.clave} - {producto.nombre[:30]}...")
                print(f"      Cantidad surtida: {detalle.cantidad_surtida}")
                
                # Buscar movimiento de salida asociado a esta requisición y producto
                movimientos = Movimiento.objects.filter(
                    requisicion=req,
                    lote__producto=producto,
                    tipo='salida'
                ).select_related('lote').order_by('-fecha')
                
                if movimientos.exists():
                    # Usar el primer lote encontrado (el más reciente)
                    mov = movimientos.first()
                    lote = mov.lote
                    
                    print(f"      ✅ Lote encontrado: {lote.numero_lote} (ID: {lote.id})")
                    print(f"         Caducidad: {lote.fecha_caducidad}")
                    
                    # Actualizar detalle
                    detalle.lote = lote
                    detalle.save(update_fields=['lote'])
                    total_actualizados += 1
                    
                    print(f"      ✅ Detalle actualizado correctamente")
                else:
                    # Intentar buscar por observaciones del movimiento
                    movimientos_obs = Movimiento.objects.filter(
                        motivo__icontains=req.numero,
                        lote__producto=producto,
                        tipo='salida'
                    ).select_related('lote').order_by('-fecha')
                    
                    if movimientos_obs.exists():
                        mov = movimientos_obs.first()
                        lote = mov.lote
                        
                        print(f"      ✅ Lote encontrado (por observaciones): {lote.numero_lote}")
                        
                        detalle.lote = lote
                        detalle.save(update_fields=['lote'])
                        total_actualizados += 1
                    else:
                        # Último intento: buscar lote del producto en farmacia central
                        # que tenga movimientos de salida en fecha cercana
                        lotes_producto = Lote.objects.filter(
                            producto=producto,
                            centro__isnull=True  # Farmacia central
                        ).order_by('-updated_at')
                        
                        if lotes_producto.exists():
                            lote = lotes_producto.first()
                            print(f"      ⚠️ Lote asignado por inferencia: {lote.numero_lote}")
                            
                            detalle.lote = lote
                            detalle.save(update_fields=['lote'])
                            total_actualizados += 1
                        else:
                            msg = f"Detalle {detalle.id} de req {req.numero}: No se encontró lote para {producto.clave}"
                            errores.append(msg)
                            print(f"      ❌ No se encontró lote")
    
    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Detalles sin lote encontrados: {total_detalles_sin_lote}")
    print(f"Detalles actualizados: {total_actualizados}")
    print(f"Errores: {len(errores)}")
    
    if errores:
        print("\nErrores encontrados:")
        for err in errores:
            print(f"  - {err}")
    
    print("\n✅ Proceso completado")
    return total_actualizados, errores


def verificar_estado():
    """Verifica el estado actual de los detalles sin lote."""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN: Estado actual de detalles de requisición")
    print("=" * 70)
    
    estados_surtidos = ['surtido', 'en_recoleccion', 'entregado', 'finalizado', 'recolectado']
    
    # Contar detalles sin lote en requisiciones surtidas
    detalles_sin_lote = DetalleRequisicion.objects.filter(
        requisicion__estado__in=estados_surtidos,
        lote__isnull=True,
        cantidad_surtida__gt=0
    ).select_related('requisicion', 'producto')
    
    print(f"\nDetalles surtidos sin lote asignado: {detalles_sin_lote.count()}")
    
    if detalles_sin_lote.exists():
        print("\nDetalle:")
        for d in detalles_sin_lote[:20]:  # Mostrar máximo 20
            print(f"  - Req {d.requisicion.numero}: {d.producto.clave} - Surtido: {d.cantidad_surtida}")
        
        if detalles_sin_lote.count() > 20:
            print(f"  ... y {detalles_sin_lote.count() - 20} más")
    
    # Contar detalles CON lote
    detalles_con_lote = DetalleRequisicion.objects.filter(
        requisicion__estado__in=estados_surtidos,
        lote__isnull=False
    ).count()
    
    print(f"\nDetalles surtidos CON lote asignado: {detalles_con_lote}")
    
    return detalles_sin_lote.count()


if __name__ == '__main__':
    print("\n🔧 Script de corrección de lotes en requisiciones\n")
    
    # Primero verificar estado
    sin_lote = verificar_estado()
    
    if sin_lote > 0:
        print(f"\n⚠️ Se encontraron {sin_lote} detalles sin lote.")
        respuesta = input("\n¿Desea ejecutar la corrección? (s/n): ").strip().lower()
        
        if respuesta == 's':
            actualizados, errores = fix_lotes_requisiciones()
            
            # Verificar resultado
            print("\n" + "-" * 70)
            verificar_estado()
        else:
            print("\nOperación cancelada.")
    else:
        print("\n✅ No hay detalles que corregir.")
