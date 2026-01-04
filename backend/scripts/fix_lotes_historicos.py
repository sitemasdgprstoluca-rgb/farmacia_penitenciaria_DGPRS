#!/usr/bin/env python
"""
Script para corregir lotes faltantes en detalles de requisiciones históricas.
Ejecutar en producción con: python manage.py shell < scripts/fix_lotes_historicos.py
"""
import os
import sys
import django

# Setup Django si no está configurado
if not django.conf.settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inventario.settings')
    django.setup()

from django.db import transaction
from core.models import Requisicion, DetalleRequisicion, Movimiento, Lote

def fix_lotes_historicos():
    """Actualiza los lotes faltantes en detalles de requisiciones históricas."""
    
    print('=' * 70)
    print('FIX: Actualizar lotes en detalles de requisiciones históricas')
    print('=' * 70)
    print()

    # Estados que indican que la requisición fue surtida
    estados_surtidos = ['surtido', 'en_recoleccion', 'entregado', 'finalizado', 'recolectado']

    # Buscar detalles que fueron surtidos pero no tienen lote asignado
    detalles_sin_lote = DetalleRequisicion.objects.filter(
        requisicion__estado__in=estados_surtidos,
        lote__isnull=True,
        cantidad_surtida__gt=0
    ).select_related('requisicion', 'producto')

    total_detalles = detalles_sin_lote.count()
    print(f'Detalles surtidos sin lote encontrados: {total_detalles}')
    
    if total_detalles == 0:
        print('✅ No hay detalles que corregir. Todo está bien!')
        return
    
    print()
    print('Procesando...')
    print()

    total_actualizados = 0
    total_por_movimiento = 0
    total_por_inferencia = 0
    errores = []

    with transaction.atomic():
        for detalle in detalles_sin_lote:
            req = detalle.requisicion
            producto = detalle.producto
            
            # Estrategia 1: Buscar movimiento de salida asociado a la requisición
            movimiento = Movimiento.objects.filter(
                requisicion=req,
                lote__producto=producto,
                tipo='salida'
            ).select_related('lote').first()
            
            if movimiento and movimiento.lote:
                detalle.lote = movimiento.lote
                detalle.save(update_fields=['lote'])
                total_actualizados += 1
                total_por_movimiento += 1
                print(f'  ✅ Req {req.numero} - {producto.clave} -> Lote {movimiento.lote.numero_lote} (por movimiento)')
            else:
                # Estrategia 2: Buscar cualquier lote disponible del producto en farmacia central
                lote = Lote.objects.filter(
                    producto=producto,
                    centro__isnull=True
                ).order_by('-fecha_caducidad').first()
                
                if lote:
                    detalle.lote = lote
                    detalle.save(update_fields=['lote'])
                    total_actualizados += 1
                    total_por_inferencia += 1
                    print(f'  ✅ Req {req.numero} - {producto.clave} -> Lote {lote.numero_lote} (inferido)')
                else:
                    # Estrategia 3: Buscar cualquier lote del producto (incluso de centros)
                    lote_cualquiera = Lote.objects.filter(producto=producto).first()
                    
                    if lote_cualquiera:
                        detalle.lote = lote_cualquiera
                        detalle.save(update_fields=['lote'])
                        total_actualizados += 1
                        total_por_inferencia += 1
                        print(f'  ✅ Req {req.numero} - {producto.clave} -> Lote {lote_cualquiera.numero_lote} (cualquier lote)')
                    else:
                        errores.append(f'Req {req.numero} - {producto.clave}: No se encontró ningún lote')
                        print(f'  ❌ Req {req.numero} - {producto.clave} - Sin lote disponible')

    print()
    print('=' * 70)
    print('RESUMEN')
    print('=' * 70)
    print(f'Total detalles procesados: {total_detalles}')
    print(f'Total actualizados: {total_actualizados}')
    print(f'  - Por movimiento encontrado: {total_por_movimiento}')
    print(f'  - Por inferencia de lote: {total_por_inferencia}')
    print(f'Errores (sin lote disponible): {len(errores)}')
    
    if errores:
        print()
        print('Errores:')
        for error in errores:
            print(f'  - {error}')
    
    print()
    print('✅ Proceso completado!')

# Ejecutar si se llama directamente
if __name__ == '__main__':
    fix_lotes_historicos()
else:
    # También ejecutar cuando se carga en shell
    fix_lotes_historicos()
