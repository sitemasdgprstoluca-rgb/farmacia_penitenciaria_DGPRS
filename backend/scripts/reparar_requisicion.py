#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para reparar una requisición que quedó en estado inconsistente:
- Estado 'entregada' pero sin movimientos de inventario
- cantidad_surtida > 0 pero no se descontó stock ni se crearon lotes en centro

Este script:
1. Revierte el estado de la requisición a 'autorizada'
2. Resetea las cantidades surtidas a 0
3. Permite que se vuelva a surtir correctamente

USO: python reparar_requisicion.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from core.models import Requisicion, Movimiento, Lote

print("=" * 80)
print("REPARACIÓN DE REQUISICIÓN INCONSISTENTE")
print("=" * 80)

# Requisición a reparar
FOLIO = 'REQ-20260112-1887'

with transaction.atomic():
    req = Requisicion.objects.select_for_update().filter(numero=FOLIO).first()
    
    if not req:
        print(f"❌ Requisición {FOLIO} no encontrada")
    else:
        print(f"\n📋 Requisición encontrada: {req.numero}")
        print(f"   Estado actual: {req.estado}")
        print(f"   Fecha surtido: {req.fecha_surtido}")
        print(f"   Fecha entrega: {req.fecha_entrega}")
        
        # Verificar movimientos
        movimientos = Movimiento.objects.filter(requisicion=req)
        print(f"\n📊 Movimientos asociados: {movimientos.count()}")
        
        if movimientos.count() > 0:
            print("   ⚠️ Ya hay movimientos - NO se puede reparar automáticamente")
            print("   Los movimientos existentes son:")
            for m in movimientos:
                print(f"      - {m.tipo}: {m.cantidad} de lote {m.lote.numero_lote if m.lote else 'N/A'}")
        else:
            print("   ✅ Sin movimientos - Procediendo con reparación...")
            
            # Mostrar detalles antes
            print("\n📦 Detalles ANTES de reparar:")
            for det in req.detalles.all():
                print(f"   - {det.producto.clave}: Solic={det.cantidad_solicitada}, "
                      f"Autoriz={det.cantidad_autorizada}, Surtido={det.cantidad_surtida}")
            
            # Confirmar
            confirmacion = input("\n¿Desea reparar esta requisición? (s/n): ")
            
            if confirmacion.lower() == 's':
                # 1. Resetear cantidades surtidas
                req.detalles.update(cantidad_surtida=0)
                print("   ✅ Cantidades surtidas reseteadas a 0")
                
                # 2. Revertir estado a 'autorizada'
                estado_anterior = req.estado
                req.estado = 'autorizada'
                req.fecha_surtido = None
                req.fecha_entrega = None
                req.surtidor = None
                req.save(update_fields=[
                    'estado', 'fecha_surtido', 'fecha_entrega', 
                    'surtidor', 'updated_at'
                ])
                print(f"   ✅ Estado revertido: {estado_anterior} → autorizada")
                
                # 3. Agregar nota de reparación
                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                req.notas = (req.notas or '') + (
                    f"\n[REPARACIÓN {timestamp}] Requisición reparada por inconsistencia. "
                    f"Estado anterior: {estado_anterior}. Sin movimientos de inventario."
                )
                req.save(update_fields=['notas'])
                
                print("\n✅ REPARACIÓN COMPLETADA")
                print(f"   La requisición {FOLIO} ahora está en estado 'autorizada'")
                print("   Puede ser surtida nuevamente desde el sistema.")
            else:
                print("\n❌ Reparación cancelada por el usuario")

print("\n" + "=" * 80)
